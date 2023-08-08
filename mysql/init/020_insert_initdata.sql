USE nico_db;

INSERT INTO scrape_config (config_type, value) VALUES 
('ARTICLE NOT EXIST CONTENTS', 'まだ記事が書かれていません'),
('ARTICLE NOT EXIST BBS', '記事が存在しないため書き込み出来ません。'),
('ARTICLE NOT EXIST CLASS', 'a-bbs_contents-empty'),                -- 記事が存在しない場合のCLASS
('RES NOT EXIST CLASS', 'st-bbs_desc');                             -- レスが存在しない場合のCLASS

INSERT INTO websites (url, name, sub_tag1, sub_tag2, sub_tag3) VALUES 
('https://dic.nicovideo.jp/', 'Niconico', 'A', NULL, NULL), 
('http://www.yahoo.com', 'Yahoo', 'Search', 'News', 'Tech'), 
('http://www.bing.com', 'Bing', 'Search', 'Microsoft', 'Tech'),
('http://www.wikipedia.org', 'Wikipedia', 'Encyclopedia', 'Knowledge', 'Education');
