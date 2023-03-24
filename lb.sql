CREATE TABLE lb_config (
    config_id SERIAL PRIMARY KEY,
    lb_algorithm VARCHAR(20) NOT NULL,
    pool_id INT NOT NULL
);

CREATE TABLE lb_pool (
    pool_id SERIAL PRIMARY KEY,
    pool_name VARCHAR(20) NOT NULL
);

CREATE TABLE lb_member (
    member_id SERIAL PRIMARY KEY,
    pool_id INT NOT NULL,
    member_ip VARCHAR(20) NOT NULL,
    member_port INT NOT NULL,
    member_weight INT DEFAULT 1
);