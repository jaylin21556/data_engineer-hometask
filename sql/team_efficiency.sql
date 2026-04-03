
-- Team-year efficiency aggregate — one row per (teamID, yearID).
-- SLG = (H + 2B + 2*3B + 3*HR) / AB  (i.e. total bases / at-bats)


CREATE OR REPLACE TABLE analytics.team_efficiency AS

WITH batting_agg AS (
    SELECT
        teamID,
        yearID,
        SUM(COALESCE(AB, 0))  AS AB,
        SUM(COALESCE(H, 0))   AS H,
        SUM(COALESCE("2B", 0)) AS "2B",
        SUM(COALESCE("3B", 0)) AS "3B",
        SUM(COALESCE(HR, 0))  AS HR
    FROM batting
    GROUP BY teamID, yearID
),

salary_agg AS (
    SELECT
        teamID,
        yearID,
        SUM(salary) AS total_payroll
    FROM salaries
    GROUP BY teamID, yearID
)

SELECT
    b.teamID,
    b.yearID,
    s.total_payroll,
    b.AB,
    b.H,
    b.HR,

    ROUND(CAST(b.H AS DOUBLE) / NULLIF(b.AB, 0), 4) AS BA,

    ROUND(
        CAST(b.H + b."2B" + 2 * b."3B" + 3 * b.HR AS DOUBLE)
        / NULLIF(b.AB, 0),
        4
    ) AS SLG,

    -- HR per million $ of payroll
    ROUND(
        CAST(b.HR AS DOUBLE) / NULLIF(s.total_payroll / 1000000.0, 0),
        4
    ) AS HR_per_Million

FROM batting_agg b
LEFT JOIN salary_agg s
    ON b.teamID = s.teamID
    AND b.yearID = s.yearID

ORDER BY b.yearID, b.teamID;
