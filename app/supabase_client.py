"""Supabase clients.

Two kinds of client are used:
- `anon_client()` reads public data (the jobs table) with the anon key.
- `user_client(session)` acts as the signed-in user, so Row Level Security limits it to that
  user's own match history. A new one is made per request because a Supabase client holds
  one user's auth state and must never be shared between users.
"""
from __future__ import annotations

import os

from supabase import Client, create_client


def is_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def anon_client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def user_client(session: dict) -> Client:
    """A client signed in as the user whose tokens are in the Flask session.

    `set_session` refreshes the access token if it has expired; the (possibly new) tokens
    are written back into the Flask session.
    """
    client = anon_client()
    response = client.auth.set_session(session["access_token"], session["refresh_token"])
    if response.session:
        session["access_token"] = response.session.access_token
        session["refresh_token"] = response.session.refresh_token
        client.postgrest.auth(response.session.access_token)
    return client
