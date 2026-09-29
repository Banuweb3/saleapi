import sys
from app import create_app
from extensions import db
from models import User

app = create_app()

def menu():
    print("\n==================================")
    print("      USER MANAGEMENT CLI         ")
    print("==================================")
    print("1. Create User")
    print("2. View Users")
    print("3. Disable User")
    print("4. Enable User")
    print("5. Delete User")
    print("6. Exit")
    print("==================================")

def create_user():
    username = input("Enter username: ").strip()
    if not username:
        print("[-] Username cannot be empty.")
        return

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print(f"[-] User '{username}' already exists.")
        return

    password = input("Enter password: ").strip()
    if not password:
        print("[-] Password cannot be empty.")
        return

    user = User(username=username)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    print(f"[+] User '{username}' created successfully! (Hashed Password stored)")

def view_users():
    users = User.query.order_by(User.id.asc()).all()
    if not users:
        print("[-] No users found in database.")
        return

    print("\n---------------------------------------------------------------------------------------------------")
    print(f"{'ID':<36} | {'Username':<20} | {'Status':<10} | {'Created At':<25}")
    print("---------------------------------------------------------------------------------------------------")
    for u in users:
        status = "Active" if u.is_active else "Disabled"
        created = u.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if u.created_at else "N/A"
        print(f"{str(u.id):<36} | {u.username:<20} | {status:<10} | {created:<25}")
    print("---------------------------------------------------------------------------------------------------")

def disable_user():
    username = input("Enter username to disable: ").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"[-] User '{username}' not found.")
        return

    if not user.is_active:
        print(f"[!] User '{username}' is already disabled.")
        return

    user.is_active = False
    db.session.commit()
    print(f"[+] User '{username}' has been disabled.")

def enable_user():
    username = input("Enter username to enable: ").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"[-] User '{username}' not found.")
        return

    if user.is_active:
        print(f"[!] User '{username}' is already active.")
        return

    user.is_active = True
    db.session.commit()
    print(f"[+] User '{username}' has been enabled.")

def delete_user():
    username = input("Enter username to delete: ").strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"[-] User '{username}' not found.")
        return

    confirm = input(f"Are you sure you want to delete user '{username}'? (y/N): ").strip().lower()
    if confirm == 'y':
        db.session.delete(user)
        db.session.commit()
        print(f"[+] User '{username}' has been deleted successfully.")
    else:
        print("[*] Deletion cancelled.")

def main():
    with app.app_context():
        while True:
            menu()
            choice = input("Select an option (1-6): ").strip()

            if choice == "1":
                create_user()
            elif choice == "2":
                view_users()
            elif choice == "3":
                disable_user()
            elif choice == "4":
                enable_user()
            elif choice == "5":
                delete_user()
            elif choice == "6":
                print("[*] Exiting User Management CLI. Goodbye!")
                sys.exit(0)
            else:
                print("[-] Invalid option. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main()
