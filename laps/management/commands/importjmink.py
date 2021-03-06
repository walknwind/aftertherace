from django.core.management.base import BaseCommand
import csv, os
from decimal import Decimal
from laps.models import MachineConfiguration, ConfigurationAttribute, Lap, Machine, Race, Racer, Track, get_or_create_race

class Command(BaseCommand):
	help = "import's a csv version of Joey's lap times Google doc"

	def handle(self, *args, **options):
		csv_file = args[0]
		if not(os.path.exists(csv_file)):
			raise CommandError("%s does not exist" % csv_file)
		counter = 0
		with open(csv_file, 'rb') as f:
			csvreader = csv.reader(f)
			index = {'Track':0, 'Date':1, 'Time':2, 'Bike':3, 'Front sprocket':4, 'Rear sprocket':5, 'Chain':6, 'Jet kit':7, 'Tires':8, 'Organization':9, 'Lap number':10, 'Lap total':11, 'Event':12, 'Weather':13, 'Source':14}
			racer, created = Racer.objects.get_or_create(first="Joey", last="Mink")
			isfirstrow = True
			for row in csvreader:
				if not(isfirstrow):
					track, created = Track.objects.get_or_create(name=row[index['Track']])

					raw_bike = row[index['Bike']]
					if raw_bike == '2009 Kawasaki Ninja 250':
						bike, created = Machine.objects.get_or_create(name="Ninjette", make="Kawasaki", model="Ninja 250", year=2009)
					else:
						raise CommandError("Unknown bike, %s" % raw_bike)

					config = MachineConfiguration.objects.create(name="config %d" % counter, machine=bike)
					
					attr, created = ConfigurationAttribute.objects.get_or_create(key='front sprocket', value=row[index['Front sprocket']])
					attr.machine_configurations.add(config)
					
					attr, created = ConfigurationAttribute.objects.get_or_create(key='rear sprocket', value=row[index['Rear sprocket']])
					attr.machine_configurations.add(config)
					
					attr, created = ConfigurationAttribute.objects.get_or_create(key='chain', value=row[index['Chain']])
					attr.machine_configurations.add(config)

					attr, created = ConfigurationAttribute.objects.get_or_create(key='jet kit', value=row[index['Jet kit']])
					attr.machine_configurations.add(config)

					# TODO: dedupe equivalent configurations?

					raw_date = row[index['Date']]
					month_day_year = raw_date.split('/')
					yyyy_mm_dd = "%s-%s-%s" % (month_day_year[2], month_day_year[0], month_day_year[1])

					race = get_or_create_race(name=row[index['Event']], date=yyyy_mm_dd, track=track, machine_config=config, organization=row[index['Organization']], conditions=row[index['Weather']])

					raw_laptime = row[index['Time']]
					first_split = raw_laptime.split(':')
					second_split = first_split[1].split('.')
					laptime = Decimal(first_split[0]) * Decimal(60) + Decimal(second_split[0]) + Decimal(0.001) * Decimal(second_split[1])
					lap = Lap.objects.create(race=race, num=row[index['Lap number']], time=laptime, racer=racer)
				else:
					isfirstrow = False
				counter = counter + 1