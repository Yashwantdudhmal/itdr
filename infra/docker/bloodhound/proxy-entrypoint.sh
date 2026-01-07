#!/bin/sh
set -eu

TEMPLATE_PATH="/etc/nginx/templates/default.conf.template"
OUT_PATH="/etc/nginx/conf.d/default.conf"

: "${BLOODHOUND_INTERNAL_TOKEN:=}"
: "${BLOODHOUND_INTERNAL_LOGIN_USERNAME:=}"
: "${BLOODHOUND_INTERNAL_LOGIN_SECRET:=}"

: "${MIDPOINT_USERNAME:=administrator}"
: "${MIDPOINT_PASSWORD:=change-me}"
: "${MIDPOINT_BASIC_AUTH:=}"

json_escape() {
  # Minimal JSON string escaping for credentials.
  # Escapes backslashes and double quotes.
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

try_bootstrap_token() {
  username="$1"
  secret="$2"

  username_esc=$(json_escape "$username")
  secret_esc=$(json_escape "$secret")

  payload=$(printf '{"login_method":"secret","username":"%s","secret":"%s"}' "$username_esc" "$secret_esc")

  payload_redacted=$(printf '%s' "$payload" | sed 's/"secret":"[^"]*"/"secret":"***"/')
  echo "[proxy-entrypoint] Login payload (redacted): $payload_redacted" >&2

  # Capture body + status code without using curl -f (we want diagnostics on non-2xx).
  resp_and_code=$(curl -sS --connect-timeout 2 --max-time 6 -X POST "http://bloodhound-app:8080/api/v2/login" -H 'Content-Type: application/json' -d "$payload" -w '\n%{http_code}' || true)
  resp_body=$(printf '%s' "$resp_and_code" | sed '$d')
  resp_code=$(printf '%s' "$resp_and_code" | tail -n 1)

  token=$(printf '%s' "$resp_body" | sed -n 's/.*"session_token":"\([^"]*\)".*/\1/p')

  if [ -n "$token" ] && [ "$resp_code" = "200" ]; then
    BLOODHOUND_INTERNAL_TOKEN="$token"
    export BLOODHOUND_INTERNAL_TOKEN
    echo "[proxy-entrypoint] Bootstrapped BloodHound session token (username=$username)." >&2
    return 0
  fi

  echo "[proxy-entrypoint] Failed to bootstrap BloodHound token (username=$username, status=$resp_code)." >&2
  if [ -n "$resp_body" ]; then
    echo "[proxy-entrypoint] Response body: $resp_body" >&2
  fi
  return 1
}

render_nginx_conf() {
  envsubst '$BLOODHOUND_INTERNAL_TOKEN $MIDPOINT_BASIC_AUTH' < "$TEMPLATE_PATH" > "$OUT_PATH"
}

bootstrap_bloodhound_token_and_reload() {
  if [ -n "$BLOODHOUND_INTERNAL_TOKEN" ]; then
    return 0
  fi

  if [ -z "$BLOODHOUND_INTERNAL_LOGIN_USERNAME" ] || [ -z "$BLOODHOUND_INTERNAL_LOGIN_SECRET" ]; then
    return 0
  fi

  # Wait for BloodHound UI and login endpoint to be reachable.
  # (We still retry token bootstrap below because BloodHound can be slow to initialize.)
  for i in $(seq 1 120); do
    ui_code=$(curl -sS --connect-timeout 2 --max-time 4 -o /dev/null -w '%{http_code}' "http://bloodhound-app:8080/ui/" || true)
    login_code=$(curl -sS --connect-timeout 2 --max-time 4 -o /dev/null -w '%{http_code}' "http://bloodhound-app:8080/api/v2/login" || true)

    # /ui/ should be 200; /api/v2/login should exist (usually 405 for GET).
    if [ "$ui_code" = "200" ] && [ "$login_code" != "000" ] && [ "$login_code" != "404" ]; then
      break
    fi
    sleep 1
  done

  # Retry token bootstrap in the background until it succeeds (or we time out).
  # This avoids a cold-start race where nginx comes up before BloodHound is ready.
  for attempt in $(seq 1 60); do
    if try_bootstrap_token "$BLOODHOUND_INTERNAL_LOGIN_USERNAME" "$BLOODHOUND_INTERNAL_LOGIN_SECRET"; then
      break
    fi

    # BloodHound's login username is typically the principal name (often "admin"), not the email.
    if [ "$BLOODHOUND_INTERNAL_LOGIN_USERNAME" != "admin" ]; then
      if try_bootstrap_token "admin" "$BLOODHOUND_INTERNAL_LOGIN_SECRET"; then
        break
      fi
    fi

    echo "[proxy-entrypoint] Token bootstrap retry $attempt/60 failed; retrying in 5s..." >&2
    sleep 5
  done

  if [ -n "$BLOODHOUND_INTERNAL_TOKEN" ]; then
    render_nginx_conf
    nginx -s reload || true
  fi
}

if [ -z "$MIDPOINT_BASIC_AUTH" ]; then
  # Used only for upstream Authorization injection. Never sent to browsers.
  # shellcheck disable=SC2005
  MIDPOINT_BASIC_AUTH=$(printf '%s:%s' "$MIDPOINT_USERNAME" "$MIDPOINT_PASSWORD" | base64 | tr -d '\n')
  export MIDPOINT_BASIC_AUTH
fi

# Start nginx immediately (do not block on token bootstrapping).
render_nginx_conf

nginx -g 'daemon off;' &
NGINX_PID=$!

trap 'kill -TERM $NGINX_PID 2>/dev/null || true' INT TERM

# Bootstrap the BloodHound token in the background and hot-reload nginx when ready.
bootstrap_bloodhound_token_and_reload &

wait $NGINX_PID
