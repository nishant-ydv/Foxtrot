-- FINAL setup: Disable RLS and insert reference data
-- Run this ENTIRE script in Supabase SQL Editor

-- Step 1: Disable RLS on all tables (we'll re-enable only on user tables later)
ALTER TABLE IF EXISTS categories DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS departments DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS scenarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS decisions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS optimization_cache DISABLE ROW LEVEL SECURITY;

-- Step 2: Insert categories
INSERT INTO categories (id, name) VALUES
    (1, 'Men''s'),
    (2, 'Women''s'),
    (3, 'Kids'''),
    (4, 'Home'),
    (5, 'Accessories')
ON CONFLICT (id) DO NOTHING;

-- Step 3: Insert departments
INSERT INTO departments (id, name, category_id) VALUES
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
ON CONFLICT (id) DO NOTHING;

-- Step 4: Verify (run this separately if needed)
SELECT 'categories' as table_name, count(*) as count FROM categories
UNION ALL
SELECT 'departments', count(*) FROM departments;
