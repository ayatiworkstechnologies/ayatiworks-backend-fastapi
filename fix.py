import sys

with open('app/services/employee_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Hide clients
old1 = """        ).filter(
            Employee.is_deleted.is_(False),
            or_(Role.code.is_(None), Role.code.notin_(["CLIENT", "SUPER_ADMIN", "ADMIN"])),
        )"""
new1 = """        ).filter(
            Employee.is_deleted.is_(False),
            ~Employee.employee_code.like("AWC%"),
            or_(Role.code.is_(None), Role.code.notin_(["CLIENT", "SUPER_ADMIN", "ADMIN"])),
        )"""
c = c.replace(old1, new1)

# 2. Allow custom code
old2 = """                # Always generate employee code on the backend to keep the sequence authoritative.
                employee_code = self.generate_employee_code()"""
new2 = """                # Use provided employee code or generate one automatically
                if employee_data.employee_code:
                    employee_code = employee_data.employee_code
                else:
                    employee_code = self.generate_employee_code()"""
c = c.replace(old2, new2)

# 3. Handle conflict
old3 = """            except SQLAlchemyIntegrityError as exc:
                self.db.rollback()
                if "employee_code" not in str(exc).lower() or attempt == 4:
                    raise"""
new3 = """            except SQLAlchemyIntegrityError as exc:
                self.db.rollback()
                if employee_data.employee_code and "employee_code" in str(exc).lower():
                    raise ValueError(f"Employee code '{employee_data.employee_code}' already exists")
                if "employee_code" not in str(exc).lower() or attempt == 4:
                    raise"""
c = c.replace(old3, new3)

with open('app/services/employee_service.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Done!')
