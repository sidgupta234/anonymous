
SELECT * FROM anon;

SELECT date_entered FROM anon;

SELECT count(*) FROM anon;

SELECT source, count(source) FROM anon GROUP BY source ORDER BY count(source) DESC;

SELECT date_entered, count(date_entered) FROM anon GROUP BY date_entered ORDER BY date_entered DESC;

SELECT link, source, phrase, title, content, date_entered FROM anon ORDER BY date_entered DESC LIMIT 100;

DELETE FROM anon WHERE content NOT LIKE "%<b>%";

CREATE TABLE anon (source, phrase, title, link PRIMARY KEY ON CONFLICT IGNORE, content, date_entered DATE);

SELECT outlets.name FROM anon LEFT OUTER JOIN outlets on anon.source = outlets.url;

SELECT * FROM anon WHERE anon.source = 'www.nytimes.com';

SELECT outlets.url FROM outlets WHERE name = 'New York Times';

SELECT name FROM outlets WHERE url = 'www.nytimes.com';
