from laps.models import ConfigurationAttribute, Lap, Machine, MachineConfiguration, Race, Track
from django.shortcuts import get_object_or_404, render, HttpResponseRedirect
from django.db.models import Q
from django.views.generic import DetailView
from braces.views import JSONResponseMixin

from django.contrib.auth.decorators import login_required

from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse

from laps import forms, util
from laps.views.user_util import assert_user_logged_in

import datetime

@login_required
def logout(request):
	return auth_views.logout(request, template_name='laps/logout.html')

class AugmentedUser:
	def __init__(self, user):
		self.user = user

	def races(self):
		return Race.objects.filter(user=self.user).order_by('date_time')

	def first_race(self):
		try:
			return Lap.objects.filter(race__user=self.user).order_by('race__date_time')[0].race
		except IndexError:
			return None

	def last_race(self):
		laps = Lap.objects.filter(race__user=self.user).order_by('-race__date_time')
		if laps.count() > 0:
			return laps[0].race
		return None

	def num_laps(self):
		return Lap.objects.filter(race__user=self.user).count()

	def tracks(self):
		return Track.objects.filter(races__user=self.user).order_by('name').distinct()

	def fastest_races(self):
		races = []
		for track in self.tracks():
			fastest_race = None
			for race in Race.objects.filter(user=self.user, track=track):
				if race.best_lap_time() is None:
					continue
				if fastest_race is None:
					fastest_race = race
				elif race.best_lap_time() < fastest_race.best_lap_time():
					fastest_race = race
			races.append(fastest_race)
		return races

def racer(request, username):
	user = get_user_model().objects.get(username=username)
	return render(request, 'laps/racer.html', {
		'racer':user.username,
		'auguser':AugmentedUser(user)})

@login_required
def profile(request):
	return racer(request, request.user.username)

class RacesByYear:
	races=None
	years=None
	dates=None

	def get_races(self, race_filter_q=Q()):
		self.races = Race.objects.filter(race_filter_q).order_by('date_time')
		self.years = []
		self.dates = []
		race_by_date={}
		for race in self.races:
			year = race.date_time.year
			if not(year in self.years):
				self.years.append(year)
			if not(race.date_time.date() in self.dates):
				self.dates.append(race.date_time.date())


def races(request, username):
	user = get_user_model().objects.get(username=username)
	races = RacesByYear()
	races.get_races(Q(user=user))
	return render(request, 'laps/races.html', {
		'racer':user.username,
		'races':races.races,
		'years':races.years,
		'dates':races.dates })

def race(request, username, race_id):
	user = get_object_or_404(get_user_model(), username=username)
	race = get_object_or_404(Race, pk=race_id, user=user)
	template_dict = {
		'racer': user.username,
		'race': race }
	if request.user.is_authenticated():
		template_dict['add_config_attr_form'] = forms.AddConfigurationAttributeToRaceForm()
	return render(request, 'laps/race.html', template_dict)

@login_required
def add_config_attr_to_race(request, username, race_id):
	user = assert_user_logged_in(username, request)
	race = get_object_or_404(Race, pk=race_id)
	if not(race.user == user):
		raise PermissionDenied

	if request.method == 'POST':
		form = forms.AddConfigurationAttributeToRaceForm(request.POST)
		if form.has_changed():
			if form.is_valid():
				key = form.cleaned_data['key']
				value = form.cleaned_data['value']
				attr, created = ConfigurationAttribute.objects.get_or_create(key=key, value=value)
				attr.machine_configurations.add(race.machine_config)
				attr.save()
	return HttpResponseRedirect(reverse('laps:race', args=(username, race.id)))



def tracks(request, username):
	user = get_object_or_404(get_user_model(), username=username)
	tracks = Track.objects.filter(races__user=user).distinct()
	return render(request, 'laps/tracks.html', {
		'racer':user.username,
		'tracks': tracks })

def track(request, username, track_id):
	user = get_object_or_404(get_user_model(), username=username)
	track = get_object_or_404(Track, pk=track_id)
	races = RacesByYear()
	races.get_races(Q(track__id=track_id))
	return render(request, 'laps/track.html', {
		'racer': user.username,
		'track': track,
		'races':races.races,
		'years':races.years,
		'dates':races.dates})

def index(request):
	return render(request, 'laps/index.html', {})

class LapTrendAJAXView(JSONResponseMixin, DetailView):
	model = Track
	json_dumps_kwargs = {u"indent": 2}

	def get(self, request, *args, **kwargs):
		username = kwargs['username']
		track_id = kwargs['track_id']

		user = get_object_or_404(get_user_model(), username=username)
		track = get_object_or_404(Track, pk=track_id)
		races = Race.objects.filter(track=track, user=user).order_by('date_time')
		result = {
			u'best': [],
			u'avg': [],
			u'race': [],
		}
		for race in races:
			result['best'].append(race.best_lap_time())
			result['avg'].append(race.average_lap_time())
			result['race'].append({
				u'date': race.date_time,
				u'name': race.name,
				u'id': race.id
				})

		return self.render_json_response(result)

class LapsAJAXView(JSONResponseMixin, DetailView):
	model = Race
	json_dumps_kwargs = {u"indent": 2}

	def get(self, request, *args, **kwargs):
		username = kwargs['username']
		race_id = kwargs['race_id']

		user = get_object_or_404(get_user_model(), username=username)
		race = get_object_or_404(Race, pk=race_id, user=user)
		result = []
		for lap in race.laps.values('num', 'time'):
			result.append({u'num': lap['num'], u'time': lap['time']})

		return self.render_json_response(result)

class TracksRacedAJAXView(JSONResponseMixin, DetailView):
	model = Race
	json_dumps_kwargs = {u"indent": 2}

	def get(self, request, *args, **kwargs):
		username = kwargs['username']
		machine_id = kwargs['machine_id']
		
		user = get_object_or_404(get_user_model(), username=username)
		machine = get_object_or_404(Machine, pk=machine_id, user=user)
		result = []
		for track in Track.objects.all().order_by('name'):
			num_races = Race.objects.filter(track=track, machine_config__machine=machine).count()
			if not(num_races == 0):
				result_item = {
						u'track': {
							u'id': track.id,
							u'name': track.name
						},
						u'num_races': num_races
					}
				result.append(result_item)

		return self.render_json_response(result)

@login_required
def create_race(request, username):
	user = assert_user_logged_in(username, request)
	if request.method == 'POST':
		form = forms.EditRaceForm(request.POST, user=user)
		if form.has_changed():
			if form.is_valid():
				machine = Machine.objects.get(name=form.cleaned_data['machine_name'], user=user)
				config = machine.empty_configuration()

				race = Race()
				race.name = form.cleaned_data['name']
				race.date_time = form.cleaned_data['date_time']
				race.track = Track.objects.get(name=form.cleaned_data['track_name'])
				race.num_laps = form.cleaned_data['num_laps']
				race.organization = form.cleaned_data['organization']
				race.machine_config = config
				race.user = user
				race.save()
				return HttpResponseRedirect(reverse('laps:edit_race_laps', args=(username, race.id)))
	else:
		form = forms.EditRaceForm(user=user)
	return render(request, 'laps/new_race.html', { 'form':form, 'racer': user.username })

@login_required
def edit_race(request, username, race_id):
	user = assert_user_logged_in(username, request)
	race = get_object_or_404(Race, pk=race_id)
	if not(race.user == user):
		raise PermissionDenied

	if request.method == 'POST':
		form = forms.EditRaceForm(request.POST, user=user)
		if form.has_changed():
			if form.is_valid():
				race.name = form.cleaned_data['name']
				race.date_time = form.cleaned_data['date_time']
				race.track = Track.objects.get(name=form.cleaned_data['track_name'])
				race.num_laps = form.cleaned_data['num_laps']
				race.organization = form.cleaned_data['organization']
				if not(race.machine_config.machine.name == form.cleaned_data['machine_name']):
					# The machine was changed
					machine = Machine.objects.get(name=form.cleaned_data['machine_name'], user=user)
					race.machine_config = machine.empty_configuration()
				race.save()
				return HttpResponseRedirect(reverse('laps:edit_race_laps', args=(username, race.id)))
	else:
		initial_form_values = race.__dict__
		initial_form_values['machine_name'] = race.machine_config.machine.name
		initial_form_values['track_name'] = race.track.name
		initial_form_values['num_laps'] = race.num_laps
		form = forms.EditRaceForm(initial_form_values, user=user)
	return render(request, 'laps/edit_race.html', { 'form':form, 'race':race, 'racer': username })

@login_required
def edit_race_laps(request, username, race_id):
	user = assert_user_logged_in(username, request)
	race = get_object_or_404(Race, pk=race_id)
	if not(race.user == user):
		raise PermissionDenied

	laps = Lap.objects.filter(race__id=race_id)
	if race.num_laps == 0:
		# No laps to enter/edit, so just return to the race page
		return HttpResponseRedirect(reverse('laps:race', args=(username, race.id)))

	if request.method == 'POST':
		# TODO: include notification to say update was successful
		form = forms.EditLapsForm(request.POST, num_laps=race.num_laps, laps=laps)
		if form.is_valid():
			lap_dict = form.get_lap_dict()
			for lap_num in xrange(1, form.num_laps + 1): # TODO: Maybe delete all laps and recreate?
				if not(lap_num in lap_dict) or not(lap_dict[lap_num]):	# no lap time given
					try:
						lap = Lap.objects.get(race=race, num=lap_num)
						lap.delete()
					except Lap.DoesNotExist:
						pass	# Lap doesn't exist? No problem
				else:	# lap time given for this lap number
					lap_time_s = util.interpret_time(lap_dict[lap_num])
					try:
						lap = Lap.objects.get(race=race, num=lap_num)
						# Update exist lap:
						lap.time = lap_time_s
					except Lap.DoesNotExist:
						# Create a new lap:
						lap, created = Lap.objects.get_or_create(race=race, num=lap_num, time=lap_time_s)
					except Lap.MultipleObjectsReturned:
						# TODO: had an issue with race that had same lap number twice...
						# TODO: maybe ensure uniqueness here?
						Lap.objects.filter(race=race, num=lap_num).delete()
						lap, created = Lap.objects.get_or_create(race=race, num=lap_num, time=lap_time_s)
					lap.save()
		else:
			raise Exception('Invalid form submission')
		return HttpResponseRedirect(reverse('laps:race', args=(username, race.id)))
	else:
		form = forms.EditLapsForm(num_laps=race.num_laps, laps=laps)
	return render(request, 'laps/edit_laps.html', { 'form':form, 'race':race, 'racer':user.username })


