SELECT us_state, tupleElement(best, 2) AS cat_id, tupleElement(best, 1) AS amount
FROM
(
    SELECT us_state, max(tuple(amount, cat_id)) AS best
    FROM homework.transactions
    GROUP BY us_state
)
ORDER BY us_state
