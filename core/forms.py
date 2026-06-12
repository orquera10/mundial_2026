from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistroUsuarioForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_config = {
            'username': {
                'label': 'Usuario',
                'placeholder': 'Tu usuario',
                'autocomplete': 'username',
            },
            'email': {
                'label': 'Email',
                'placeholder': 'tu@email.com',
                'autocomplete': 'email',
            },
            'first_name': {
                'label': 'Nombre',
                'placeholder': 'Tu nombre',
                'autocomplete': 'given-name',
            },
            'last_name': {
                'label': 'Apellido',
                'placeholder': 'Tu apellido',
                'autocomplete': 'family-name',
            },
            'password1': {
                'label': 'Contrasena',
                'placeholder': 'Crea una contrasena',
                'autocomplete': 'new-password',
            },
            'password2': {
                'label': 'Repetir contrasena',
                'placeholder': 'Repeti la contrasena',
                'autocomplete': 'new-password',
            },
        }
        for name, config in field_config.items():
            field = self.fields[name]
            field.label = config['label']
            field.widget.attrs.update({
                'class': 'auth-input',
                'placeholder': config['placeholder'],
                'autocomplete': config['autocomplete'],
            })
