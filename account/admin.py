from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    UserChangeForm as BaseUserChangeForm,
    AdminUserCreationForm as BaseUserCreationForm,
)  
from account.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

# Register your models here.
class UserCreationForm(BaseUserCreationForm):
    """ A Form for creating new users. Includes all the required
    fields, plus a repeated password
    """
    password1 = forms.CharField(label='Password', 
                            widget=forms.PasswordInput
                            )
    password2 = forms.CharField(label="Confirm Password",
                            widget=forms.PasswordInput        
                            )
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = BaseUserCreationForm.Meta.fields + ('balance','is_staff','is_active')


    def clean_password2(self):
        #check that two password entry match
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Password doesnot match")
        return password2

    def save(self, commit=True):
        # save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data.get('password1'))
        if commit:
            user.save()
        return user


class UserChangeForm(BaseUserChangeForm):
    """ A form for updating users. Includes all the fields
    but replace the password with Admin hash password display
    fields
    """

    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = BaseUserChangeForm.Meta.fields 
                

    def clean_password(self):
        # regardless of what user provide return initial
        return self.initial['password']

class UserAdmin(BaseUserAdmin):
    change = UserChangeForm
    add_form = UserCreationForm
    model = User
    list_display = ('username','first_name', 'last_name', 
                    'balance','token','is_staff',)
    list_filter = ('is_staff',)
    fieldsets = (
        (None, {'fields': ('email', 'password',)}),
        ('Personal info', {'fields': ('first_name','last_name',)}),
        ('Permissions', {'fields': ('is_staff',)}),
        ('Balance info', {'fields': ('balance',)}),
    )

    search_fields = ('email', 'username',)
    ordering = ('-email',)
    filter_horizontal = ()
    

admin.site.register(User, UserAdmin)

