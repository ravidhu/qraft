---
description: One row per author with post and engagement metrics
macros: [qraft_utils.scalar]
tags: [mart, blog]
---
-- ref('stg_authors') pulls in the author dimension.
-- ref('int_posts_enriched') pulls in the already-enriched post layer,
-- so Qraft runs this model only after both upstream models are complete.
SELECT
    a.author_id,
    a.author_name,
    a.email,
    a.joined_at,
    COUNT(p.post_id)                    AS total_posts,
    coalesce_zero(SUM(p.comment_count)) AS total_comments_received,
    coalesce_zero(AVG(p.comment_count)) AS avg_comments_per_post,
    MAX(p.published_at)                 AS last_published_at
FROM ref('stg_authors') a
LEFT JOIN ref('int_posts_enriched') p ON a.author_id = p.author_id
GROUP BY a.author_id, a.author_name, a.email, a.joined_at
