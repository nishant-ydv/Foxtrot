-- Clean setup: Drop and recreate tables WITHOUT RLS
-- Run this ENTIRE script in Supabase SQL Editor at once

-- Drop existing tables (if any)
drop table if exists decisions cascade;
drop table if exists optimization_cache cascade;
drop table if exists scenarios cascade;
drop table if exists departments cascade;
drop table if exists categories cascade;

-- Recreate categories (NO RLS)
create table categories (
    id serial primary key,
    name text not null,
    created_at timestamptz default now()
);

-- Recreate departments (NO RLS)
create table departments (
    id serial primary key,
    name text not null,
    category_id int references categories(id),
    created_at timestamptz default now()
);

-- Recreate scenarios (with RLS for user data)
create table scenarios (
    id uuid primary key default gen_random_uuid(),
    user_id uuid,
    session_id text,
    dept_id int not null,
    dept_name text,
    budget numeric(12, 2) not null,
    service_target numeric(5, 2) not null,
    season text default 'Fall/Holiday',
    nl_input text,
    feasible boolean,
    achieved_service numeric(5, 2),
    total_cost numeric(12, 2),
    minimum_budget numeric(12, 2),
    configs jsonb,
    narration text,
    created_at timestamptz default now(),
    tags text[]
);

-- Recreate optimization_cache
create table optimization_cache (
    id uuid primary key default gen_random_uuid(),
    cache_key text unique not null,
    budget numeric(12, 2) not null,
    service_target numeric(5, 2) not null,
    dept_id int not null,
    season text not null,
    result jsonb not null,
    created_at timestamptz default now(),
    expires_at timestamptz default now() + interval '7 days'
);

-- Recreate decisions
create table decisions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid,
    session_id text,
    dept_id int not null,
    context text not null,
    budget numeric(12, 2),
    current_service numeric(5, 2),
    options jsonb,
    recommendation text,
    chosen_option text,
    chosen_at timestamptz,
    created_at timestamptz default now()
);

-- Insert reference data
insert into categories (id, name) values
    (1, 'Men''s'),
    (2, 'Women''s'),
    (3, 'Kids''),
    (4, 'Home'),
    (5, 'Accessories');

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
    (112, 'Jewelry', 5);

-- Verify
select 'categories' as table_name, count(*) as count from categories
union all
select 'departments', count(*) from departments;
