import random

def get_random_persona():
    personas = [
        {
            "name": "Anitha",
            "age": 65,
            "tone": "Nervous, Tamil-English mix, uses 'Ayyo' and 'Kanna'",
            "flaw": "Bad eyesight, types slowly, very gullible initially"
        },
        {
            "name": "Ramesh",
            "age": 50,
            "tone": "Overconfident, Hindi-English mix, calls everyone 'Boss'",
            "flaw": "Thinks he is smarter than the scammer, asks technical questions wrong"
        },
        {
            "name": "Susan",
            "age": 21,
            "tone": "Polite student, scared of authority",
            "flaw": "Afraid of police/legal action, apologizes constantly"
        }
    ]
    return random.choice(personas)