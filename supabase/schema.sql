-- Foxtrot Supabase Schema
-- Free tier: 500MB storage, pausing after 7 days inactivity

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ============================================
-- USERS & SESSIONS (for future auth)
-- ============================================

-- User profiles (optional - link to Supabase Auth)
create table if not exists user_profiles (
    id uuid primary key default uuid_generate_v4(),
    auth_user_id uuid references auth.users(id) on delete cascade,
    email text unique,
    full_name text,
    role text default 'cbo',  -- 'cbo', 'planner', 'admin'
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ============================================
-- DEPARTMENTS & CATEGORIES (reference data)
-- ============================================

create table if not exists categories (
    id serial primary key,
    name text not null,
    created_at timestamptz default now()
);

create table if not exists departments (
    id serial primary key,
    name text not null,
    category_id int references categories(id),
    created_at timestamptz default now()
);

-- ============================================
-- SCENARIOS (user-generated what-if scenarios)
-- ============================================

create table if not exists scenarios (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references user_profiles(id) on delete set null,
    session_id text,  -- For anonymous users (Streamlit session)

    -- Input parameters
    dept_id int not null,
    dept_name text,
    budget numeric(12, 2) not null,
    service_target numeric(5, 2) not null,
    season text default 'Fall/Holiday',

    -- Natural language input (if any)
    nl_input text,

    -- Results
    feasible boolean,
    achieved_service numeric(5, 2),
    total_cost numeric(12, 2),
    minimum_budget numeric(12, 2),

    -- Policy configs (JSONB for flexibility)
    configs jsonb,
    narration text,

    -- Metadata
    created_at timestamptz default now(),
    tags text[],  -- User tags like ['baseline', 'optimistic']

    -- Row Level Security will be added later when auth is enabled
    constraint budget_positive check (budget > 0),
    constraint service_range check (service_target >= 0 and service_target <= 100)
);

-- Index for fast scenario history lookup
create index if not exists idx_scenarios_session on scenarios(session_id);
create index if not exists idx_scenarios_user on scenarios(user_id);
create index if not exists idx_scenarios_dept on scenarios(dept_id);
create index if not exists idx_scenarios_created on scenarios(created_at desc);

-- ============================================
-- OPTIMIZATION RESULTS (cached calculations)
-- ============================================

create table if not exists optimization_cache (
    id uuid primary key default uuid_generate_v4(),
    cache_key text unique not null,  -- Hash of (budget, service_target, dept_id, season)

    -- Input
    budget numeric(12, 2) not null,
    service_target numeric(5, 2) not null,
    dept_id int not null,
    season text not null,

    -- Result
    result jsonb not null,

    created_at timestamptz default now(),
    expires_at timestamptz default now() + interval '7 days'
);

create index if not exists idx_cache_key on optimization_cache(cache_key);
create index if not exists idx_cache_expires on optimization_cache(expires_at);

-- ============================================
-- DECISION LOG (high-stakes decisions)
-- ============================================

create table if not exists decisions (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references user_profiles(id) on delete set null,
    session_id text,

    dept_id int not null,
    context text not null,
    budget numeric(12, 2),
    current_service numeric(5, 2),

    -- Decision options (JSONB)
    options jsonb,
    recommendation text,

    -- User's final choice (if they made one)
    chosen_option text,
    chosen_at timestamptz,

    created_at timestamptz default now()
);

-- ============================================
-- SAMPLE DATA
-- ============================================

-- Insert categories
insert into categories (id, name) values
    (1, 'Men''s'),
    (2, 'Women''s'),
    (3, 'Kids''),
    (4, 'Home'),
    (5, 'Accessories')
on conflict (id) do nothing;

-- Insert departments
insert into departments (id, name, category_id) values
    (101, 'Men''s Shoes', 1),
    (102, 'Men''s Apparel', 1),
    (103, 'Men''s Accessories', 1),
    (104, 'Women''s Shoes', 2),
    (105, 'Women''s Apparel', 2),
    (106, 'Women''s Accessories', 2),
    (107, 'Kids'' Shoes', 3),
    (108, 'Kids'' Apparel', 3),
    (109, 'Home Textiles', 4),
    (110, 'Home Decor', 4),
    (111, 'Handbags', 5),
    (112, 'Jewelry', 5)
on conflict (id) do nothing;

-- ============================================
-- ROW LEVEL SECURITY (when auth is enabled)
-- ============================================

-- Enable RLS on scenarios
alter table scenarios enable row level security;

-- Policy: users can only see their own scenarios (by user_id or session_id)
create policy "Users can view own scenarios"
    on scenarios for select
    using (
        auth.uid() = user_id
        or session_id = current_setting('app.session_id', true)
    );

create policy "Users can insert own scenarios"
    on scenarios for insert
    with check (
        auth.uid() = user_id
        or session_id = current_setting('app.session_id', true)
    );

-- Similar for decisions
alter table decisions enable row level security;

create policy "Users can view own decisions"
    on decisions for select
    using (auth.uid() = user_id or session_id = current_setting('app.session_id', true));

create policy "Users can insert own decisions"
    on decisions for insert
    with check (auth.uid() = user_id or session_id = current_setting('app.session_id', true));

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to clean expired cache entries
create or replace function clean_expired_cache()
returns void as $$
begin
    delete from optimization_cache where expires_at < now();
end;
$$ language plpgsql;

-- Function to get scenario history for a session
create or replace function get_session_scenarios(p_session_id text)
returns table (
    id uuid,
    dept_name text,
    budget numeric,
    service_target numeric,
    feasible boolean,
    achieved_service numeric,
    created_at timestamptz
) as $$
begin
    return query
    select s.id, s.dept_name, s.budget, s.service_target,
           s.feasible, s.achieved_service, s.created_at
    from scenarios s
    where s.session_id = p_session_id
    order by s.created_at desc
    limit 50;
end;
$$ language plpgsql;
