#!/bin/sh
set -eu

TEMPLATE_PATH="/etc/nginx/templates/default.conf.template"
OUT_PATH="/etc/nginx/conf.d/default.conf"

: "${BLOODHOUND_INTERNAL_TOKEN:=}"
: "${BLOODHOUND_INTERNAL_LOGIN_USERNAME:=}"
: "${BLOODHOUND_INTERNAL_LOGIN_SECRET:=}"

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
  resp_and_code=$(curl -sS -X POST "http://bloodhound-app:8080/api/v2/login" -H 'Content-Type: application/json' -d "$payload" -w '\n%{http_code}' || true)
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

if [ -z "$BLOODHOUND_INTERNAL_TOKEN" ] && [ -n "$BLOODHOUND_INTERNAL_LOGIN_USERNAME" ] && [ -n "$BLOODHOUND_INTERNAL_LOGIN_SECRET" ]; then
  # Wait for BloodHound UI and login endpoint to be reachable.
  for i in $(seq 1 60); do
    ui_code=$(curl -sS -o /dev/null -w '%{http_code}' "http://bloodhound-app:8080/ui/" || true)
    login_code=$(curl -sS -o /dev/null -w '%{http_code}' "http://bloodhound-app:8080/api/v2/login" || true)

    # /ui/ should be 200; /api/v2/login should exist (usually 405 for GET).
    if [ "$ui_code" = "200" ] && [ "$login_code" != "000" ] && [ "$login_code" != "404" ]; then
      break
    fi
    sleep 1
  done

  if ! try_bootstrap_token "$BLOODHOUND_INTERNAL_LOGIN_USERNAME" "$BLOODHOUND_INTERNAL_LOGIN_SECRET"; then
    # BloodHound's login username is typically the principal name (often "admin"), not the email.
    if [ "$BLOODHOUND_INTERNAL_LOGIN_USERNAME" != "admin" ]; then
      try_bootstrap_token "admin" "$BLOODHOUND_INTERNAL_LOGIN_SECRET" || true
    fi
  fi
fi

envsubst '$BLOODHOUND_INTERNAL_TOKEN' < "$TEMPLATE_PATH" > "$OUT_PATH"
exec nginx -g 'daemon off;'
