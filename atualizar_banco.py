from fixcity.factory import create_app
from fixcity.db import get_db

app = create_app()

with app.app_context():
    try:
        db = get_db()
        
        # Garante que o banco correto está selecionado
        db.execute("USE FixcityDB;")
        
        try:
            # 1. Tenta adicionar a coluna já com DEFAULT 1 (Privado por padrão)
            db.execute("ALTER TABLE usuarios ADD COLUMN is_private TINYINT(1) NOT NULL DEFAULT 1 AFTER is_admin;")
            print("✅ Coluna 'is_private' criada com sucesso com DEFAULT 1!")
        except Exception as e:
            # 2. Se a coluna já existia (ex: criada anteriormente com DEFAULT 0), atualiza o DEFAULT e os dados existentes
            print(f"ℹ️ Coluna já existe, atualizando o padrão para 1... ({e})")
            db.execute("ALTER TABLE usuarios ALTER COLUMN is_private SET DEFAULT 1;")
            db.execute("UPDATE usuarios SET is_private = 1 WHERE is_private = 0;")
            print("✅ Coluna 'is_private' atualizada para DEFAULT 1 e registros convertidos!")

        # Confirma as alterações
        if hasattr(db, 'commit'):
            db.commit()
            
    except Exception as e:
        print(f"⚠️ Mensagem de erro do banco: {e}")