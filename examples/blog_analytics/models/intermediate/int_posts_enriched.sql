---
description: Published posts enriched with comment counts
tags: [intermediate, blog]
---
-- ref('stg_posts') and ref('stg_comments') make Qraft aware of the
-- dependency: this model cannot run until both staging models are ready.
SELECT
    p.post_id,
    p.author_id,
    p.title,
    p.published_at,
    LENGTH(p.body)      AS body_length,
    COUNT(c.comment_id) AS comment_count
FROM ref('stg_posts') p
LEFT JOIN ref('stg_comments') c ON p.post_id = c.post_id
WHERE LENGTH(p.body) >= {{ min_post_length }}
GROUP BY p.post_id, p.author_id, p.title, p.published_at, p.body
