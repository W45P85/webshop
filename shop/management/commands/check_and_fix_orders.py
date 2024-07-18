import os
import logging
import uuid
from django.core.management.base import BaseCommand
from shop.models import Order, OrderdArticle, Adress, Customer, Article
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from datetime import datetime
from django.db import transaction, connection, IntegrityError

# Logging konfigurieren
log_dir = 'log_files'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(log_dir, f'order_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Command(BaseCommand):
    help = 'Überprüft die Vollständigkeit der Bestellungen, zeigt Abweichungen an und generiert fehlende Daten nach.'

    def handle(self, *args, **kwargs):
        with open(log_filename, 'a') as log_file:
            self.cleanup_invalid_order_ids(log_file)

            incomplete_orders = []
            orders = Order.objects.all()

            for order in orders:
                issues = []
                order_modified = False

                # Prüfen, ob ein Customer verknüpft ist
                if not order.customer or not order.customer.user:
                    issues.append('Kein verknüpfter Kunde')
                    self.stdout.write(self.style.WARNING(f'Bestellung {order.id}: Kein verknüpfter Kunde gefunden. Erstelle Dummy-Kunde...'))
                    log_file.write(f'Bestellung {order.id}: Kein verknüpfter Kunde gefunden. Erstelle Dummy-Kunde...\n')
                    # Erstellen eines Dummy-Kunden
                    user = User.objects.create_user(username=get_random_string(10), email='dummy@example.com', password='dummy_password')
                    customer = Customer.objects.create(user=user)
                    order.customer = customer
                    order_modified = True

                # Prüfen, ob mindestens ein OrderdArticle existiert
                if not OrderdArticle.objects.filter(order=order).exists():
                    issues.append('Keine Artikel in der Bestellung')
                    self.stdout.write(self.style.WARNING(f'Bestellung {order.id}: Keine Artikel gefunden. Erstelle Dummy-Artikel...'))
                    log_file.write(f'Bestellung {order.id}: Keine Artikel gefunden. Erstelle Dummy-Artikel...\n')
                    # Erstellen eines Dummy-Artikels und einer Bestellung
                    article = Article.objects.first()  # Verwenden eines bestehenden Artikels
                    if not article:
                        article = Article.objects.create(name='Dummy Artikel', price=0)
                    OrderdArticle.objects.create(order=order, article=article, quantity=1)
                    order_modified = True

                # Prüfen, ob eine Adresse existiert
                if not Adress.objects.filter(order=order).exists():
                    issues.append('Keine Adresse verknüpft')
                    self.stdout.write(self.style.WARNING(f'Bestellung {order.id}: Keine Adresse gefunden. Erstelle Dummy-Adresse...'))
                    log_file.write(f'Bestellung {order.id}: Keine Adresse gefunden. Erstelle Dummy-Adresse...\n')
                    # Erstellen einer Dummy-Adresse
                    Adress.objects.create(order=order, customer=order.customer, address='Dummy Address', city='Dummy City', state='Dummy State', zipcode='12345')
                    order_modified = True

                # Prüfen, ob eine Bestellnummer eine gültige UUID ist
                if not self.is_valid_uuid(order.order_id):
                    issues.append('Bestellnummer ist keine gültige UUID')
                    self.stdout.write(self.style.WARNING(f'Bestellung {order.id}: Bestellnummer ist keine gültige UUID. Generiere neue Bestellnummer...'))
                    log_file.write(f'Bestellung {order.id}: Bestellnummer ist keine gültige UUID. Generiere neue Bestellnummer...\n')
                    # Generieren einer neuen UUID für die Bestellnummer
                    new_order_id = uuid.uuid4()
                    order.order_id = str(new_order_id)
                    order_modified = True

                if order_modified:
                    order.done = True
                    order.save()
                    self.stdout.write(self.style.SUCCESS(f'Bestellung {order.id}: Änderungen gespeichert und Bestellung als erledigt markiert.'))
                    log_file.write(f'Bestellung {order.id}: Änderungen gespeichert und Bestellung als erledigt markiert.\n')

                if issues:
                    incomplete_orders.append({
                        'order_id': order.id,
                        'issues': issues
                    })

            # Abweichungen anzeigen
            if incomplete_orders:
                for entry in incomplete_orders:
                    self.stdout.write(self.style.WARNING(f"Bestellung {entry['order_id']} hatte folgende Probleme und wurde korrigiert: {', '.join(entry['issues'])}"))
                    log_file.write(f"Bestellung {entry['order_id']} hatte folgende Probleme und wurde korrigiert: {', '.join(entry['issues'])}\n")
            else:
                self.stdout.write(self.style.SUCCESS('Alle Bestellungen waren bereits vollständig.'))
                log_file.write('Alle Bestellungen waren bereits vollständig.\n')

        self.stdout.write(self.style.SUCCESS(f'Einige Bestellungen wurden korrigiert. Details siehe {os.path.abspath(log_filename)}'))

    def is_valid_uuid(self, uuid_to_test):
        if uuid_to_test is None or uuid_to_test == '':
            return False
        try:
            uuid.UUID(uuid_to_test)
            return True
        except ValueError:
            return False

    def cleanup_invalid_order_ids(self, log_file):
        with transaction.atomic():
            with connection.cursor() as cursor:
                try:
                    cursor.execute("SELECT id, order_id FROM shop_order")
                    rows = cursor.fetchall()

                    for row in rows:
                        order_id = row[1]
                        if order_id is None or order_id == '':
                            new_order_id = uuid.uuid4()
                            log_file.write(f'Bestellung {row[0]}: Bereinige fehlende Bestellnummer. Neue Bestellnummer: {new_order_id}\n')
                            self.stdout.write(self.style.WARNING(f'Bestellung {row[0]}: Bereinige fehlende Bestellnummer. Neue Bestellnummer: {new_order_id}'))
                            cursor.execute(
                                "UPDATE shop_order SET order_id = %s WHERE id = %s",
                                [str(new_order_id), row[0]]
                            )
                        else:
                            try:
                                uuid.UUID(order_id)
                            except ValueError:
                                new_order_id = uuid.uuid4()
                                log_file.write(f'Bestellung {row[0]}: Bereinige ungültige Bestellnummer. Neue Bestellnummer: {new_order_id}\n')
                                self.stdout.write(self.style.WARNING(f'Bestellung {row[0]}: Bereinige ungültige Bestellnummer. Neue Bestellnummer: {new_order_id}'))
                                cursor.execute(
                                    "UPDATE shop_order SET order_id = %s WHERE id = %s",
                                    [str(new_order_id), row[0]]
                                )

                except IntegrityError as e:
                    log_file.write(f'IntegrityError in cleanup_invalid_order_ids: {str(e)}\n')
                    self.stdout.write(self.style.ERROR(f'IntegrityError in cleanup_invalid_order_ids: {str(e)}'))
