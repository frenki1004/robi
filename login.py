"""One-time Ecovacs login. Run it yourself in a terminal:

    uv run login.py

It asks for your ECOVACS HOME email and password (the password is used once and
never saved), handles the email code, and writes .env.local with a long-lived
account token plus a secret key for the phone link.
"""

from __future__ import annotations

import asyncio
import getpass
import secrets
import sys
import time
from pathlib import Path

import aiohttp

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.exceptions import (
    AuthenticationError,
    DeviceVerificationRequiredError,
    InvalidVerificationCodeError,
)
from deebot_client.models import AccountCredentials
from deebot_client.util import md5

ENV_FILE = Path(__file__).parent / ".env.local"


def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    out = {}
    for line in ENV_FILE.read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep:
            out[k.strip()] = v.strip().strip('"')
    return out


async def main() -> None:
    old = read_env()
    email = input(f"Ecovacs email [{old.get('ROBI_EMAIL', '')}]: ").strip() or old.get("ROBI_EMAIL", "")
    password = getpass.getpass("Ecovacs password (not saved): ")
    country = (input(f"Country code [{old.get('ROBI_COUNTRY', 'HR')}]: ").strip()
               or old.get("ROBI_COUNTRY", "HR")).upper()
    if not email or not password:
        sys.exit("Email and password are required.")

    same_account = old.get("ROBI_EMAIL") == email and old.get("ROBI_COUNTRY") == country
    device_id = (same_account and old.get("ROBI_DEVICE_ID")) or md5(str(time.time()))

    captured: list[AccountCredentials] = []

    async def on_account(c: AccountCredentials) -> None:
        captured.append(c)

    async with aiohttp.ClientSession() as session:
        rest = create_rest_config(session, device_id=device_id, alpha_2_country=country)
        auth = Authenticator(rest, email, md5(password))
        auth.subscribe_account_credentials(on_account)
        del password

        try:
            await auth.authenticate()
        except DeviceVerificationRequiredError:
            await auth.request_device_verification_code()
            print("Ecovacs sent a code to your email.")
            while True:
                try:
                    await auth.verify_device(input("Code: "))
                    break
                except InvalidVerificationCodeError:
                    print("Wrong code, try again.")
        except AuthenticationError as ex:
            sys.exit(f"Login failed: {ex}")

        await asyncio.sleep(0.1)  # let the credentials callback run
        if not captured:
            sys.exit("Login worked but no account token came back; please report this.")
        acc = captured[-1]

        devices = await ApiClient(auth).get_devices()
        await auth.teardown()

    if not devices.mqtt:
        names = [d.get("deviceName") for d in devices.not_supported + devices.xmpp]
        sys.exit(f"No supported robot found on this account. Found: {names or 'nothing'}")
    names = [d.api.get("nick") or d.api.get("deviceName") for d in devices.mqtt]
    print(f"Found robot: {', '.join(names)}  (Robi uses the first one)")

    values = {
        "ROBI_EMAIL": email,
        "ROBI_COUNTRY": country,
        "ROBI_DEVICE_ID": device_id,
        "ROBI_USER_ID": acc.user_id,
        "ROBI_ACCESS_TOKEN": acc.access_token,
        "ROBI_KEY": old.get("ROBI_KEY") or secrets.token_urlsafe(18),
    }
    ENV_FILE.write_text("".join(f'{k}="{v}"\n' for k, v in values.items()))
    ENV_FILE.chmod(0o600)
    print(f"Saved {ENV_FILE.name}. Start the app with:  uv run app.py")


if __name__ == "__main__":
    asyncio.run(main())
