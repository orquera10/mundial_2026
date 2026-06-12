from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('paises/', views.paises, name='paises'),
    path('predicciones/', views.predicciones, name='predicciones'),
    path('almanaque/', views.almanaque, name='almanaque'),
    path('selecciones/<int:equipo_id>/', views.seleccion_detalle, name='seleccion_detalle'),
    path('selecciones/<int:equipo_id>/favorito/', views.alternar_pais_favorito, name='alternar_pais_favorito'),
    path('partidos/<int:partido_id>/', views.partido_detalle, name='partido_detalle'),
    path('partidos/<int:partido_id>/favorito/', views.alternar_favorito, name='alternar_favorito'),
    path('partidos/<int:partido_id>/prediccion/', views.guardar_prediccion, name='guardar_prediccion'),
    path('partidos/<int:partido_id>/prediccion/reset/', views.resetear_prediccion, name='resetear_prediccion'),
    path('predicciones/reset/', views.resetear_todas_predicciones, name='resetear_todas_predicciones'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro/', views.registro, name='registro'),
    path('api/partidos-vivo/', views.api_partidos_vivo, name='api_partidos_vivo'),
]
