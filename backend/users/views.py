from django.shortcuts import render, redirect 
from django.contrib.auth.forms import AuthenticationForm 
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Book
from django.contrib.auth import login
from .forms import CustomUserCreationForm, PasswordResetRequestForm, SetNewPasswordForm, ChangeNameForm, DeleteAccountForm, ChangePasswordForm
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import secrets
import string
from collections import Counter
from backend import utils




def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  
            user.save()
            send_confirmation_email(request, user)
            return redirect("users:registration_pending")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})

def send_confirmation_email(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    activation_link = request.build_absolute_uri(
        reverse("users:activate", kwargs={"uidb64": uid, "token": token})
    )
    subject = "Activate Your Leadtheread Account"
    message = f"Hi {user.name},\n\nPlease click the link below to activate your account:\n\n{activation_link}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def activate_view(request, uidb64, token):
    User = get_user_model()

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return redirect('users:user_home')
    else:
        return render(request, "users/activation_invalid.html")  
    

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))

def reset_password_view(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = get_user_model().objects.filter(email=email).first()
            if user:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = request.build_absolute_uri(
                    reverse("users:confirm_password_reset", kwargs={"uidb64": uid, "token": token})
                )
                
                subject = "Password Reset Request"
                message = (
                f"Hi {user.name},\n\n"
                f"Please click the link below to reset your password:\n\n{reset_link}\n\n"
                f"If you did not request to reset your password, you can safely ignore this message."
                )
                
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
                return redirect("users:registration_pending")
    else:
        form = PasswordResetRequestForm()
    
    return render(request,'users/reset_password.html', {"form": form})

def confirm_password_reset(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetNewPasswordForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data['new_password']
                user.set_password(new_password)
                user.save()
                login(request, user)
                return redirect('users:user_home')
        else:
            form = SetNewPasswordForm()
        return render(request, 'users/set_new_password.html', {
            "form": form,
            "uidb64": uidb64,
            "token": token
        })
    else:
        return render(request, 'users/activation_invalid.html')


def login_view(request): 
    if request.method == "POST": 
        form = AuthenticationForm(data=request.POST)
        if form.is_valid(): 
            login(request, form.get_user())
            return redirect("users:user_home")
    else: 
        form = AuthenticationForm()
    return render(request, "users/login.html", { "form": form })

def registration_pending_view(request):
    return render(request,"users/registration_pending.html")

def activation_invalid_view(request):
    return render(request,"users/activation_invalid.html")

@login_required(login_url="/users/login/")
def user_home_view(request):
    liked_books = list(request.user.liked_books.all())
    liked_books.reverse()

    genre_count = Counter()

    for book in liked_books:
        # Assuming book has a genres field that stores genres as a string
        _, genres = book.genres.split("Genres: ")
        genres_list = genres.split(", ")
        genre_count.update(genres_list)

    top_genres = [genre for genre, count in genre_count.most_common(3)]

    if not top_genres:
        top_genres = ["No Books Liked Yet!"]

    return render(request, "users/user_home.html", {"liked_books" : liked_books,"top_genres":top_genres})

@login_required(login_url="/users/login/")
def logout_view(request):
    if request.method == "POST": 
        logout(request)
        return redirect('homepage')  
    else:
        return redirect('homepage')
    
@login_required(login_url="/users/login/")
def settings_view(request):
    change_name_form = ChangeNameForm(user=request.user)
    change_password_form = ChangePasswordForm()
    delete_account_form = DeleteAccountForm()

    return render(request, 'users/settings.html', {
        'change_name_form': change_name_form,
        'change_password_form': change_password_form,
        'delete_account_form': delete_account_form,
    })


# Handles login required itself
def toggle_book(request):
    if not request.user.is_authenticated:
        return JsonResponse({'redirect_url': '/users/login/'}, status=401)
    if request.method == 'POST':
        isbn = request.POST.get('isbn')
        title = request.POST.get('title')
        authors = request.POST.get('authors')
        image_link = request.POST.get('image_link')
        buy_link = request.POST.get('buy_link')
        genres = request.POST.get('genres')

        #Looks up by isbn  
        book, created = Book.objects.get_or_create(
                isbn=isbn,
                defaults={'title': title, 'authors': authors, 'image_link': image_link, 'buy_link': buy_link,'genres':genres}
            )

        if request.user in book.users.all():
            book.users.remove(request.user)
            # removed so query to liked book will always exist
            # if not book.users.exists():
            #     book.delete()
            liked = False
        else:
            # Book is being liked
            genres = utils.get_book_genres(isbn)
            book.genres = genres
            book.users.add(request.user)
            liked = True

        #minhash      
        # add a sucess pair (query_vector to isbn)
        # Example: "Magic boy goes to hogwarts" -> vectorization & PCA -> [368x] : "Harry Potter and The Sorcerors Stone"
        if liked:
            query = request.POST.get("query")
            utils.update_minhash(key=isbn,query=query)
        return JsonResponse({'message': 'success', 'liked': liked}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url="/users/login/")
def change_name(request):
    if request.method == "POST":
        form = ChangeNameForm(request.POST, user=request.user)
        if form.is_valid():
            new_name = form.cleaned_data['new_name']
            user = request.user
            user.name = new_name  # Assuming 'name' is the field in your user model
            user.save()
            return redirect('users:settings')  # Redirect back to settings page after successful name change
    else:
        form = ChangeNameForm(user=request.user)
    
    return render(request, 'users/settings.html', {'change_name_form': form})

@login_required(login_url="/users/login/")
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = request.user
            user.set_password(new_password)
            user.save()
            return redirect('users:settings')  # Redirect back to settings page after successful password change
    else:
        form = ChangePasswordForm()
    
    return render(request, 'users/settings.html', {'change_password_form': form})

@login_required(login_url="/users/login/")
def delete_account(request):
    if request.method == "POST":
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            user = request.user
            user.delete()  
            return redirect('homepage') 
    else:
        form = DeleteAccountForm()
    
    return render(request, 'users/settings.html', {'delete_account_form': form})



@login_required(login_url="/users/login/")
def list_liked_books(request):
    liked_books = request.user.liked_books.all()
    return JsonResponse({'liked_books':liked_books})