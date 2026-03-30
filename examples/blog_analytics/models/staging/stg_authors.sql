---
description: Raw authors from the blog source
tags: [staging, blog]
columns:
  - name: author_id
    description: Unique author identifier
    tests:
      - not_null
      - unique
  - name: email
    description: Author email address
    tests:
      - not_null
---
SELECT
    author_id,
    name        AS author_name,
    email,
    joined_at
FROM source('blog', 'authors')
