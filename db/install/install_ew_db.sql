
-- Run all the sql in teh postdeployment folder
\i '/home/bojank/Projects/ew/db/install/postdeployment/ew_auth.sql'

-- Spring cleaning
VACUUM ANALYZE;
