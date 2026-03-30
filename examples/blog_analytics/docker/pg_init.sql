-- Seed data for blog_analytics example
-- Source: blog application database (PostgreSQL)

CREATE SCHEMA IF NOT EXISTS blog_raw;

-- Authors
CREATE TABLE blog_raw.authors (
    author_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    joined_at   DATE NOT NULL
);

INSERT INTO blog_raw.authors (author_id, name, email, joined_at) VALUES
    (1, 'Alice Chen',    'alice@techblog.io',  '2023-01-15'),
    (2, 'Bob Martinez',  'bob@techblog.io',    '2023-03-22'),
    (3, 'Carol Wu',      'carol@techblog.io',  '2023-06-10'),
    (4, 'David Kim',     'david@techblog.io',  '2023-09-01'),
    (5, 'Eva Johansson', 'eva@techblog.io',    '2024-01-05');

-- Posts
CREATE TABLE blog_raw.posts (
    post_id     INTEGER PRIMARY KEY,
    author_id   INTEGER NOT NULL REFERENCES blog_raw.authors(author_id),
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    published_at DATE NOT NULL
);

INSERT INTO blog_raw.posts (post_id, author_id, title, body, published_at) VALUES
    (1, 1, 'Getting Started with SQL',          'SQL is the language of data...', '2023-02-01'),
    (2, 1, 'Advanced Window Functions',          'Window functions let you...', '2023-04-15'),
    (3, 2, 'Data Modeling Best Practices',       'When designing your schema...', '2023-05-20'),
    (4, 3, 'Introduction to Trino',              'Trino is a distributed SQL...', '2023-07-12'),
    (5, 2, 'ETL vs ELT',                         'The debate between ETL and ELT...', '2023-08-30'),
    (6, 4, 'Building Data Pipelines',            'Modern data pipelines should...', '2023-10-05'),
    (7, 3, 'Iceberg Table Format',               'Apache Iceberg provides...', '2023-11-18'),
    (8, 5, 'SQL Templating with Qraft',          'Qraft helps you manage SQL...', '2024-02-14');

-- Comments
CREATE TABLE blog_raw.comments (
    comment_id  INTEGER PRIMARY KEY,
    post_id     INTEGER NOT NULL REFERENCES blog_raw.posts(post_id),
    author_name TEXT NOT NULL,
    body        TEXT NOT NULL,
    created_at  DATE NOT NULL
);

INSERT INTO blog_raw.comments (comment_id, post_id, author_name, body, created_at) VALUES
    (1,  1, 'reader_jane',   'Great intro!',                       '2023-02-02'),
    (2,  1, 'sql_fan',       'Very helpful, thanks.',              '2023-02-03'),
    (3,  2, 'data_dev',      'Window functions are amazing.',      '2023-04-16'),
    (4,  2, 'analyst_mike',  'Could you cover QUALIFY next?',      '2023-04-17'),
    (5,  3, 'junior_eng',    'This clarified a lot for me.',       '2023-05-21'),
    (6,  4, 'trino_user',    'We use Trino in production!',        '2023-07-13'),
    (7,  4, 'data_dev',      'How does it compare to Spark SQL?',  '2023-07-14'),
    (8,  5, 'architect_sam', 'ELT is the way to go.',              '2023-09-01'),
    (9,  6, 'reader_jane',   'Bookmarked this one.',               '2023-10-06'),
    (10, 7, 'lake_lover',    'Iceberg changed everything for us.', '2023-11-19'),
    (11, 7, 'sql_fan',       'What about Delta Lake?',             '2023-11-20'),
    (12, 8, 'new_user',      'Just tried Qraft, love it!',        '2024-02-15');
