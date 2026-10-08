from django.forms import ModelForm
from django.forms.widgets import TextInput
from .models import Color

#Color Picker for Admin Panel form
class ColorForm(ModelForm):
    class Meta:
        model = Color
        fields = "__all__"
        widgets = {
            "hex_code": TextInput(attrs={"type": "color"}),
        }
    def __init__(self, *args, **kwargs):
        super(ColorForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields["hex_code"].widget = TextInput(
                attrs={"type": "color", "title": self.instance.hex_code}
            )    