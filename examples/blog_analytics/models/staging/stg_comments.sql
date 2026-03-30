---
description: Raw comments from the blog source
tags: [staging, blog]
---
SELECT
    comment_id,
    post_id,
    author_name AS commenter_name,
    body,
    created_at
FROM source('blog', 'comments')
