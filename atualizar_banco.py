from fixcity.factory import create_app
from fixcity.db import get_db

app = create_app()

with app.app_context():
    try:
        db = get_db()
        
        # Garante que o banco correto está selecionado
        db.execute("USE FixcityDB;")
        
        # Executa o comando para adicionar a coluna de privacidade
        db.execute("ALTER TABLE usuarios ADD COLUMN is_private TINYINT(1) NOT NULL DEFAULT 0 AFTER is_admin;")
        
        # Se o seu objeto db exigir commit manual
        if hasattr(db, 'commit'):
            db.commit()
            
        print("✅ Coluna 'is_private' adicionada com sucesso no MySQL!")
    except Exception as e:
        print(f"⚠️ Mensagem do banco: {e}")