import redis

# Connect to Redis
r = redis.Redis(host='10.8.0.1', port=6379, db=0)

# Initialize the game
game_over = False
used_words = set()

# Get a random word from the database
word = r.srandmember('words').decode('utf-8')
used_words.add(word)

# Print the starting word and prompt the user for the next word
print(f"The starting word is '{word}'.")
next_word = input("Enter the next word: ")

# Loop until the game is over
while not game_over:
    # Check if the next word is a valid choice
    if next_word not in used_words and r.zscore('words', next_word) is not None and word[-1] == next_word[0]:
        # The next word is valid, so add it to the used words set and update the current word
        used_words.add(next_word)
        word = next_word
        print(f"Good choice! The current word is '{word}'.")

        # Check if there are any words that can be linked from the current word
        linked_words = r.zrangebylex('words', f"[{word}]".encode('utf-8'), f"[{word}\xff]".encode('utf-8'))
        valid_words = [w.decode('utf-8') for w in linked_words if w.decode('utf-8') not in used_words]

        # If there are no valid linked words, the game is over
        if not valid_words:
            game_over = True
            print("There are no more valid words. Game over!")
        else:
            # Prompt the user for the next word
            next_word = input(f"Choose a word starting with '{word[-1]}': ")
    else:
        # The next word is not a valid choice, so prompt the user to try again
        next_word = input(f"Sorry, '{next_word}' is not a valid choice. Please try again: ")
