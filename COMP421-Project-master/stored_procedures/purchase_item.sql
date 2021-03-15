
-- Purchases an item for a player given the item id and their username
-- It adds the item to the ownership table and updates the coin balance
-- Some error conditions that this procedure covers:
--   1. Insufficient balance
--   2. Player already owns the item (no double pay)
--   3. If the item is an attachment, this code ensures the player already owns the item the attachment is for
--
-- The procedure returns the updated coin balance of the player.
CREATE OR REPLACE FUNCTION purchase_item(_item_id INTEGER, _username VARCHAR)
RETURNS INTEGER
AS $$
DECLARE
    coin_balance INTEGER;
    item_price INTEGER;
    owns_attached_to BOOLEAN;
BEGIN
    -- Check if the user has enough coin balance
    coin_balance := (SELECT players.coin_balance FROM players WHERE username = _username);
    item_price := (SELECT price FROM items WHERE id = _item_id);

    IF item_price > coin_balance THEN
        RAISE 'User % has insufficient balance to purchase this item', _username;
    ELSIF EXISTS(SELECT 1 FROM owns WHERE item_id = _item_id AND owns.username = _username) THEN
        RAISE 'User % already owns this item', _username;
    ELSE
        -- If the item is an attachment we can't purchase it unless we own the item it attaches to
        IF EXISTS(SELECT 1 FROM attachments WHERE item_id = _item_id) THEN
           owns_attached_to := EXISTS(
               SELECT 1 FROM owns
               INNER JOIN attachments
                 ON owns.item_id = attachments.attaches_to_id
               WHERE attachments.item_id = _item_id);

            IF NOT owns_attached_to THEN
                RAISE 'User % is attempting to purchase an attachment without owning the item it attaches to', _username;
            END IF;
        END IF;
        UPDATE players
        SET coin_balance = players.coin_balance - item_price
        WHERE players.username = _username;

        INSERT INTO owns (username, item_id)
        VALUES (_username, _item_id);

        RETURN coin_balance - item_price;
    END IF;
END;
$$
LANGUAGE plpgsql;