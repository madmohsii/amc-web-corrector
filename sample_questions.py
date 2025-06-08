# Exemple de données pour créer un QCM
SAMPLE_QUESTIONS = [
    {
        'text': 'Quelle est la capitale de la France ?',
        'choices': [
            {'text': 'Paris', 'correct': True},
            {'text': 'Londres', 'correct': False},
            {'text': 'Berlin', 'correct': False},
            {'text': 'Madrid', 'correct': False}
        ]
    },
    {
        'text': 'Combien font 2 + 2 ?',
        'choices': [
            {'text': '3', 'correct': False},
            {'text': '4', 'correct': True},
            {'text': '5', 'correct': False},
            {'text': '6', 'correct': False}
        ]
    },
    {
        'text': 'Quel est le plus grand océan du monde ?',
        'choices': [
            {'text': 'Océan Atlantique', 'correct': False},
            {'text': 'Océan Indien', 'correct': False},
            {'text': 'Océan Pacifique', 'correct': True},
            {'text': 'Océan Arctique', 'correct': False}
        ]
    },
    {
        'text': 'En quelle année a eu lieu la révolution française ?',
        'choices': [
            {'text': '1789', 'correct': True},
            {'text': '1792', 'correct': False},
            {'text': '1776', 'correct': False},
            {'text': '1804', 'correct': False}
        ]
    },
    {
        'text': 'Quelle est la formule chimique de l\'eau ?',
        'choices': [
            {'text': 'H2O', 'correct': True},
            {'text': 'CO2', 'correct': False},
            {'text': 'NaCl', 'correct': False},
            {'text': 'O2', 'correct': False}
        ]
    }
]

# Configuration de notation
SCORING_STRATEGIES = {
    'default': {
        'name': 'Standard',
        'description': 'Bonne réponse: +1, Mauvaise: 0, Vide: 0',
        'params': 'default'
    },
    'negative': {
        'name': 'Avec pénalité',
        'description': 'Bonne réponse: +1, Mauvaise: -0.5, Vide: 0',
        'params': '(b=1,m=0,v=-0.5)'
    },
    'strict': {
        'name': 'Strict',
        'description': 'Bonne réponse: +1, Mauvaise: -1, Vide: 0',
        'params': '(b=1,m=0,v=-1)'
    }
}
