---
description: Raw blog posts from the blog source
tags: [staging, blog]
columns:
  - name: post_id
    description: Unique post identifier
    tests:
      - not_null
      - unique
  - name: author_id
    description: Author who wrote the post
    tests:
      - not_null
      - relationships:
          to: ref('stg_authors')
          field: author_id
---
SELECT
    post_id,
    author_id,
    title,
    body,
    published_at
FROM source('blog', 'posts')
