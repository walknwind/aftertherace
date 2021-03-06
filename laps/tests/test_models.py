from django.test import TestCase
from laps.models import Machine, MachineConfiguration, ConfigurationAttribute
from laps import models
from datetime import datetime
from django.contrib.auth import get_user_model
from decimal import Decimal

class MachineTest(TestCase):

	def test_save(self):
		u,created = get_user_model().objects.get_or_create(username='user1', email='user1@joeymink.com')
		m = Machine(name='Ninjette Test', make='Kawi', model='EX250', year=2009, user=u)
		m.save()

		mFromDb = Machine.objects.get(id=m.id)
		self.assertTrue(mFromDb.name == 'Ninjette Test')

class MachineConfigurationTest(TestCase):

	def test_save(self):
		u,created = get_user_model().objects.get_or_create(username='user1', email='user1@joeymink.com')
		m = Machine(name='Ninjette Test', make='Kawi', model='EX250', year=2009, user=u)
		m.save()
		c = MachineConfiguration(name='My Config', machine=m)
		c.save()

		mc = MachineConfiguration.objects.get(id=c.id)
		self.assertTrue(c.machine.make == 'Kawi')

		# Test reverse relationship
		readMachine = Machine.objects.get(id=m.id)
		self.assertTrue(readMachine.configurations.all()[0].name == 'My Config')

class ConfigurationAttributeTest(TestCase):

	def test_save(self):
		u,created = get_user_model().objects.get_or_create(username='user1', email='user1@joeymink.com')
		m = Machine(name='Ninjette Test', make='Kawi', model='EX250', year=2009, user=u)
		m.save()
		c = MachineConfiguration(name='My Config', machine=m)
		c.save()
		attr = ConfigurationAttribute(key='chain', value='non-oring 520')
		attr.save()
		attr.machine_configurations.add(c)

		readConfigAttr = ConfigurationAttribute.objects.get(id=attr.id)
		self.assertTrue(readConfigAttr.machine_configurations.get().name == c.name)

		readMachine = Machine.objects.get(id=m.id)
		self.assertTrue(readMachine.configurations.all()[0].attributes.all()[0].value == 'non-oring 520')

class RaceTest(TestCase):

	def test_five_lap_race(self):
		u,created = get_user_model().objects.get_or_create(username='user1', email='user1@joeymink.com')
		m = Machine(name='Ninja 250', make='Kawasaki', model='Ninja 250', year=2009, user=u)
		m.save()
		c = MachineConfiguration(name='My Config', machine=m)
		c.save()
		attr = ConfigurationAttribute(key='chain', value='non-oring 520')
		attr.save()
		attr.machine_configurations.add(c)

		t = models.Track(name="NJMP Thunderbolt")
		t.save()
		race = models.Race(name="Ultra Lightweight Thunderbike", track=t, machine_config=c, date_time=datetime.now(), user=u)
		race.save()

		racer = models.Racer(first="Joey")
		racer.save()

		for i in range(0, 5):
			l = models.Lap(race=race, num=(i + 1), time=Decimal(1.21))
			l.save()

		self.assertTrue(models.Race.objects.get(id=race.id).laps.count() == 5)

class TrackTest(TestCase):

	def test_only_given_users_machines_returned(self):
		t = models.Track(name="NJMP Thunderbolt")
		t.save()

		# User 1
		u1,created = get_user_model().objects.get_or_create(username='user1', email='user1@joeymink.com')

		m1 = Machine(name='User1 Bike', make='Kawi', model='EX250', year=2009, user=u1)
		m1.save()
		c1 = MachineConfiguration(name='My Config', machine=m1)
		c1.save()

		race1 = models.Race(name="Ultra Lightweight Thunderbike", track=t, machine_config=c1, date_time=datetime.now(), user=u1)
		race1.save()

		# User 2
		u2,created = get_user_model().objects.get_or_create(username='user2', email='user2@joeymink.com')

		m2 = Machine(name='User2 Bike', make='Kawi', model='EX250', year=2009, user=u2)
		m2.save()
		c2 = MachineConfiguration(name='My Config', machine=m2)
		c2.save()

		race2 = models.Race(name="Ultra Lightweight Thunderbike", track=t, machine_config=c2, date_time=datetime.now(), user=u2)
		race2.save()

		machines_for_u1 = t.machines(u1)
		self.assertTrue(len(machines_for_u1) == 1)
		self.assertTrue(machines_for_u1[0].name == m1.name)

		machines_for_u2 = t.machines(u2)
		self.assertTrue(len(machines_for_u2) == 1)
		self.assertTrue(machines_for_u2[0].name == m2.name)