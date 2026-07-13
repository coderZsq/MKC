UPDATE resources r
JOIN (
  SELECT resource_id, status
  FROM tasks t1
  WHERE id = (
    SELECT MAX(id) FROM tasks t2 WHERE t2.resource_id = t1.resource_id
  )
) latest ON r.id = latest.resource_id
SET r.status = CASE
  WHEN latest.status = 'running' THEN 2
  WHEN latest.status = 'completed' THEN 3
  WHEN latest.status = 'failed' THEN 4
  ELSE r.status
END;
