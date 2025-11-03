#!/usr/bin/env python3
"""
Inicializácia Turso databázy pre Finance Tracker
"""
import sys
from database_client import db_client

def init_database():
    """Inicializuje databázu so schémou"""
    print("🚀 Inicializujem Turso databázu...")
    print("")
    
    try:
        # Načítaj SQL schému
        with open('database_schema_turso.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Rozdeľ na jednotlivé príkazy
        commands = []
        current_command = []
        
        for line in sql_content.split('\n'):
            # Preskočiť komentáre
            if line.strip().startswith('--'):
                continue
            
            current_command.append(line)
            
            # Ak riadok končí `;`, je to koniec príkazu
            if line.strip().endswith(';'):
                command = '\n'.join(current_command).strip()
                if command:
                    commands.append(command)
                current_command = []
        
        # Vykonaj každý príkaz
        success_count = 0
        error_count = 0
        
        for i, command in enumerate(commands, 1):
            try:
                # Skip prázdne príkazy
                if not command or command == ';':
                    continue
                
                db_client.execute(command)
                
                # Zisti typ príkazu pre lepší output
                cmd_type = command.split()[0].upper()
                if cmd_type == 'CREATE':
                    if 'TABLE' in command.upper():
                        table_name = command.split('TABLE')[1].split('(')[0].strip().split()[0]
                        print(f"  ✓ Vytvorená tabuľka: {table_name}")
                    elif 'INDEX' in command.upper():
                        print(f"  ✓ Vytvorený index")
                    elif 'VIEW' in command.upper():
                        view_name = command.split('VIEW')[1].split('AS')[0].strip().split()[0]
                        print(f"  ✓ Vytvorený view: {view_name}")
                elif cmd_type == 'INSERT':
                    print(f"  ✓ Vložené základné dáta")
                
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                # Ignoruj "already exists" chyby
                if 'already exists' in error_msg.lower():
                    print(f"  ⚠ Už existuje (preskakujem)")
                else:
                    print(f"  ✗ Chyba: {error_msg}")
                    error_count += 1
        
        print("")
        print(f"✅ Hotovo! Úspešných: {success_count}, Chýb: {error_count}")
        print("")
        
        # Overenie
        print("🔍 Overujem vytvorené tabuľky...")
        result = db_client.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        print("")
        print("📊 Tabuľky v databáze:")
        for row in result.rows:
            print(f"  • {row[0]}")
        
        print("")
        
        # Overenie kategórií
        result = db_client.execute("SELECT COUNT(*) FROM Categories")
        count = result.rows[0][0]
        print(f"✅ Počet kategórií: {count}")
        
        if count > 0:
            result = db_client.execute("SELECT Name, Icon FROM Categories LIMIT 5")
            print("")
            print("📝 Prvých 5 kategórií:")
            for row in result.rows:
                print(f"  {row[1]} {row[0]}")
        
        print("")
        print("🎉 Databáza je pripravená na použitie!")
        
        return 0
        
    except FileNotFoundError:
        print("❌ Súbor database_schema_turso.sql nebol nájdený!")
        print("   Uistite sa, že ste v správnom priečinku.")
        return 1
        
    except Exception as e:
        print(f"❌ Chyba pri inicializácii databázy: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(init_database())

