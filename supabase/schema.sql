-- Job Explorer schema. Run this once in Supabase: Dashboard -> SQL Editor -> New query -> Run.

-- Jobs scraped from Internshala, cleaned by scripts/seed_supabase.py
create table if not exists public.jobs (
    id               bigint generated always as identity primary key,
    title            text        not null,
    company          text        not null,
    experience_years integer,                 -- null when the listing doesn't say
    salary_min       integer,                 -- yearly, in rupees; null when not mentioned
    salary_max       integer,
    skills           text[]      not null default '{}',
    perks            text[]      not null default '{}',
    cities           text[]      not null default '{}',
    is_hybrid        boolean     not null default false,
    url              text        not null unique,
    scraped_at       timestamptz
);

create index if not exists jobs_skills_idx on public.jobs using gin (skills);
create index if not exists jobs_cities_idx on public.jobs using gin (cities);

-- Each saved CV match belongs to the signed-in user who ran it.
create table if not exists public.match_history (
    id          uuid        primary key default gen_random_uuid(),
    user_id     uuid        not null default auth.uid() references auth.users (id) on delete cascade,
    cv_name     text        not null,
    cv_skills   text[]      not null default '{}',
    matches     jsonb       not null,
    created_at  timestamptz not null default now()
);

create index if not exists match_history_user_idx on public.match_history (user_id, created_at desc);

-- Row Level Security: anyone may read jobs; users only see and change their own history.
alter table public.jobs          enable row level security;
alter table public.match_history enable row level security;

drop policy if exists "jobs are public" on public.jobs;
create policy "jobs are public" on public.jobs
    for select to anon, authenticated using (true);

drop policy if exists "read own history" on public.match_history;
create policy "read own history" on public.match_history
    for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "insert own history" on public.match_history;
create policy "insert own history" on public.match_history
    for insert to authenticated with check ((select auth.uid()) = user_id);

drop policy if exists "delete own history" on public.match_history;
create policy "delete own history" on public.match_history
    for delete to authenticated using ((select auth.uid()) = user_id);
