from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("registar/", views.signup, name="signup"),
    path("horario/", views.schedule, name="schedule"),
    path("pacotes/", views.packages, name="packages"),
    path("privacidade/", views.privacidade, name="privacidade"),
    path("marcar/<int:session_id>/", views.book, name="book"),
    path("as-minhas-marcacoes/", views.my_bookings, name="my_bookings"),
    path("cancelar/<int:booking_id>/", views.cancel_booking, name="cancel_booking"),
]
