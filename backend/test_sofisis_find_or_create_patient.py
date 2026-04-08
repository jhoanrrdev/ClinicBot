from src.integrations.sofisis_patient import SofisisPatientClient

client = SofisisPatientClient()

result = client.find_or_create_patient(
    first_name="Jhoan",
    last_name="Prueba",
    identification="12345678999",
    email="jhoan.prueba.clinicbot+1@gmail.com",
    cell="573111234567",
    phone="573111234567",
    address="Bello, Antioquia",
    city="Bello",
    state="Antioquia",
)

print(result)