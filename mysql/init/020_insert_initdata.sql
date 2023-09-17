USE nico_db;

INSERT INTO scrape_config (config_type, value) VALUES 
('ARTICLE NOT EXIST CONTENTS', 'まだ記事が書かれていません'),
('ARTICLE NOT EXIST BBS', '記事が存在しないため書き込み出来ません。'),
('ARTICLE NOT EXIST CLASS', 'a-bbs_contents-empty'),                -- 記事が存在しない場合のCLASS
('RES NOT EXIST CLASS', 'st-pg_contents');                             -- レスが存在しない場合のCLASS

INSERT INTO websites (url, name, sub_tag1, sub_tag2, sub_tag3) VALUES 
('https://dic.nicovideo.jp/', 'Niconico', 'A', NULL, NULL), 
('http://www.yahoo.com', 'Yahoo', 'Search', 'News', 'Tech'), 
('http://www.bing.com', 'Bing', 'Search', 'Microsoft', 'Tech'),
('http://www.wikipedia.org', 'Wikipedia', 'Encyclopedia', 'Knowledge', 'Education');

INSERT INTO article_list (article_id, title, url, last_res_id, moved, new_id) VALUES 
(100001, 'Artikel', 'https://example.de/artikel1', 52, True, 200001),
(20002345, '技術の進化', 'https://sample.jp/tech', 1320, False, -1),
(5220830, '土葬', 'https://dic.nicovideo.jp/a/%E5%9C%9F%E8%91%AC', 0, False, -1), 
(473859, 'Linux', 'https://dic.nicovideo.jp/a/linux', 29, False, -1), 
(430509, 'ubuntu', 'https://dic.nicovideo.jp/a/ubuntu', 152, False, -1), 
(340, 'Innovation', 'https://innovate.com', 7, False, -1),
(4567890, '花と風', 'https://nature.jp/flower_wind', 2450, True, 5000000),
(5678, 'Mix文', 'https://mix.com/lang', 3, False, -1),
(91011, '034211', 'https://einfach.de', 78, True, 121314),
(1215, '数字だけ', 'https://numbers.com', 9101112, False, -1);
