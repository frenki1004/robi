# Robi

A one-screen phone app for an Ecovacs Deebot: tap the rooms, tap **Počni čistiti**.
While it cleans there are only two buttons: **Pauza** and **Završi i vrati na stanicu** (End and Dock).
There is no "Stop returning" button, and Start is locked while the station empties the dust bin or washes the mops.

What the screen tells you:
- what the robot is doing (docked, cleaning with minutes and m², paused, returning)
- **robot needs help**, with the problem in plain Croatian (stuck, lifted, brush tangled, water tank empty, …)
- **robot not reachable** (switched off or no Wi-Fi)
- station busy (emptying dust, washing or drying mops) and low battery

It talks to the Ecovacs cloud through [`deebot-client`](https://github.com/DeebotUniverse/client.py),
the unofficial library used by Home Assistant. An Ecovacs update can break it until the library catches up
(`uv lock --upgrade-package deebot-client`, then redeploy).

## 1. Log in to Ecovacs (once, on your computer)

```bash
uv run login.py
```

It asks for the ECOVACS HOME email, password and country, then a code Ecovacs emails you.
The password is never saved. It writes `.env.local` with an account token and a secret key.

## 2. Run it

**Locally:** `uv run app.py` prints a link for your phone (same Wi-Fi).

**On Vercel** (live at https://robi-lime.vercel.app): push the values from `.env.local` and redeploy:

```bash
./push-env.sh
```

Then open `https://robi-lime.vercel.app/#k=<ROBI_KEY>` once on the phone and "Add to Home Screen".
The phone remembers the key; anyone without it gets "Nema pristupa".
To lock out old phones, change `ROBI_KEY` in `.env.local` and push again.

## Try it without a robot

```bash
ROBI_DEMO=1 uv run app.py
```

Then open `http://localhost:8080/#k=demo`. Picking **Kupaonica** shows what an error looks like.
