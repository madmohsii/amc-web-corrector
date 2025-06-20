import csv

# Lire la liste des étudiants
names_map = {}
with open('liste.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Utiliser l'ID comme clé et construire le nom complet
        student_id = row['id'].lstrip('0')  # Enlever les zéros devant (001 -> 1)
        full_name = f"{row['nom']} {row['prenom']}"
        names_map[student_id] = full_name

print("Noms trouvés:", names_map)

# Lire et corriger le fichier des notes
with open('exports/notes.csv', 'r') as file:
    content = file.read()

# Remplacer les "?" par les vrais noms
for student_id, name in names_map.items():
    old_line = f'"{student_id}","","?","0"'
    new_line = f'"{student_id}","","{name}","0"'
    content = content.replace(old_line, new_line)
    print(f"Remplacement: {old_line} -> {new_line}")

# Sauvegarder le fichier corrigé
with open('exports/notes.csv', 'w') as file:
    file.write(content)

print("Fichier CSV corrigé !")
