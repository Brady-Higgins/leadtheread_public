from django.urls import path 
from . import views 

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name="register"),
    path("activate/<uidb64>/<token>/", views.activate_view, name="activate"),
    path('registration_pending/', views.registration_pending_view, name="registration_pending"),
    path('activation_invalid/', views.activation_invalid_view, name="activation_invalid"),
    path('reset_password/', views.reset_password_view, name='reset_password'),
    path('confirm-password-reset/<uidb64>/<token>/', views.confirm_password_reset, name='confirm_password_reset'),
    path('login/', views.login_view, name="login"),
    path('user_home/', views.user_home_view, name="user_home"),
    path('logout/', views.logout_view, name="logout"),
    path('settings/', views.settings_view, name="settings"),
    path('change_name/', views.change_name, name="change_name"),
    path('change_password/', views.change_password, name="change_password"),
    path('delete_account/', views.delete_account, name="delete_account"),
    path('toggle_book/', views.toggle_book, name="toggle_book")

]
