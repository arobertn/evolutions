CREATE TABLE soup (
    id        INT         PRIMARY KEY,
    name      VARCHAR(64) NOT NULL,
    is_dairy  BOOL        NOT NULL
  );

INSERT INTO soup (id, name, is_dairy) VALUES (1, 'Lentil', FALSE);
INSERT INTO soup (id, name, is_dairy) VALUES (2, 'Minestrone', FALSE);
