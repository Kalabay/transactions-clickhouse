SELECT us_state, tupleElement(best, 2) AS cat_id, tupleElement(best, 1) AS amount
FROM
(
    SELECT us_state, maxMerge(best) AS best
    FROM homework.state_maximums
    GROUP BY us_state
)
ORDER BY us_state
