-- Fix RLS policies for reference tables
-- Run this in Supabase SQL Editor

-- Disable RLS on reference tables (public data, no auth needed)
alter table categories disable row level security;
alter table departments disable row level security;

-- Insert reference data (will now work)
insert into categories (id, name) values
    (1, 'Men''s'),
    (2, 'Women''s'),
    (3, 'Kids'''),
    (4, 'Home'),
    (5, 'Accessories')
on conflict (id) do nothing;

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

-- Verify
select 'categories' as table_name, count(*) as count from categories
union all
select 'departments', count(*) from departments;
