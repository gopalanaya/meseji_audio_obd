from smscampaign.models import SmsTemplate
from django import forms
from django.core.validators import RegexValidator
from smscampaign.tasks import send_test_message

number_validator = RegexValidator(r'^[6-9][0-9]+', 'Valid Mobile Number Only')

class SmsTemplateForm(forms.ModelForm):
    class Meta:
        model = SmsTemplate
        fields = ('name', 'header', 'pe_id', 'template_id', 'message')


class SmsTestForm(forms.ModelForm):
    number = forms.CharField(max_length=12, min_length=10, help_text="Test Number to get sms", validators=[number_validator])

    class Meta:
        model = SmsTemplate
        fields = ('message',)
    
    def __init__(self, *args, **kwargs):
        super(SmsTestForm, self).__init__(*args, **kwargs)
        self.fields['message'].widget.attrs.update({'readonly': 'readonly'})
        self.fields['message'].help_text = "Cannot be modified from here"


    def send_message(self):
        number = self.cleaned_data.get('number')
        data = self.instance.get_test_data(number=number)
        status = send_test_message(data=data)
        # update the status as sent
        self.instance.test_status = '-'.join(status)
        self.instance.save()


        





