from django import forms
from django.core.validators import FileExtensionValidator, MaxLengthValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from .models import Sidequest, SidequestSubmission, Boss, Punishment, StatusEffect
import os


class SidequestForm(forms.ModelForm):
    """Form untuk create/edit sidequest dengan validation"""
    class Meta:
        model = Sidequest
        fields = ['title', 'description', 'instructions', 'due_date', 'exp_reward', 'late_exp_reward', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'maxlength': 2000}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'maxlength': 5000}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'exp_reward': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10000}),
            'late_exp_reward': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 10000}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise ValidationError('Title is required.')
        if len(title) < 3:
            raise ValidationError('Title must be at least 3 characters long.')
        return title
    
    def clean_exp_reward(self):
        exp_reward = self.cleaned_data.get('exp_reward', 0)
        if exp_reward < 0:
            raise ValidationError('EXP reward cannot be negative.')
        if exp_reward > 10000:
            raise ValidationError('EXP reward cannot exceed 10000.')
        return exp_reward
    
    def clean_late_exp_reward(self):
        late_exp_reward = self.cleaned_data.get('late_exp_reward', 0)
        exp_reward = self.cleaned_data.get('exp_reward', 0)
        if late_exp_reward < 0:
            raise ValidationError('Late EXP reward cannot be negative.')
        if late_exp_reward > exp_reward:
            raise ValidationError('Late EXP reward cannot exceed regular EXP reward.')
        return late_exp_reward
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date:
            from django.utils import timezone
            if due_date < timezone.now():
                raise ValidationError('Due date cannot be in the past.')
        return due_date


class SubmissionForm(forms.ModelForm):
    """Form untuk submit sidequest dengan file upload security"""
    # Max file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.zip', '.rar', '.txt', '.jpg', '.jpeg', '.png']
    
    class Meta:
        model = SidequestSubmission
        fields = ['submitted_file']
        widgets = {
            'submitted_file': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': '.pdf,.doc,.docx,.zip,.rar,.txt,.jpg,.jpeg,.png'
            }),
        }
    
    def clean_submitted_file(self):
        file = self.cleaned_data.get('submitted_file')
        if not file:
            raise ValidationError('Please select a file to upload.')
        
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f'File size cannot exceed {self.MAX_FILE_SIZE / (1024*1024):.1f}MB.')
        
        # Check file extension
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f'Invalid file type. Allowed types: {", ".join(self.ALLOWED_EXTENSIONS)}'
            )
        
        # Check for dangerous file names
        dangerous_patterns = ['..', '/', '\\', '\x00']
        for pattern in dangerous_patterns:
            if pattern in file.name:
                raise ValidationError('Invalid file name.')
        
        return file


class GradeSubmissionForm(forms.ModelForm):
    """Form untuk grade submission dengan validation"""
    class Meta:
        model = SidequestSubmission
        fields = ['grade', 'feedback']
        widgets = {
            'grade': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'maxlength': 1000}),
        }
    
    def clean_grade(self):
        grade = self.cleaned_data.get('grade')
        if grade is not None:
            if grade < 0 or grade > 100:
                raise ValidationError('Grade must be between 0 and 100.')
        return grade
    
    def clean_feedback(self):
        feedback = self.cleaned_data.get('feedback', '').strip()
        if feedback and len(feedback) > 1000:
            raise ValidationError('Feedback cannot exceed 1000 characters.')
        return feedback


class BossForm(forms.ModelForm):
    """Form untuk create/edit boss"""
    class Meta:
        model = Boss
        fields = ['type', 'name', 'description', 'base_score', 'user', 'battle_date']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'base_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'battle_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter hanya players
        self.fields['user'].queryset = self.fields['user'].queryset.filter(role='player')


class PunishmentForm(forms.ModelForm):
    """Form untuk create/edit punishment"""
    evidence_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'JSON format (optional): {"key": "value"}'
        }),
        help_text='JSON format untuk evidence (optional)'
    )
    
    class Meta:
        model = Punishment
        fields = ['user', 'type', 'severity', 'description', 'exp_penalty', 'status_effect', 'duration_days']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'exp_penalty': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'status_effect': forms.Select(attrs={'class': 'form-select'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Filter hanya players
        self.fields['user'].queryset = self.fields['user'].queryset.filter(role='player')
        # Set status_effect sebagai optional
        self.fields['status_effect'].required = False
        
        # Convert evidence JSON to string for display
        if self.instance and self.instance.pk and self.instance.evidence:
            import json
            self.fields['evidence_json'].initial = json.dumps(self.instance.evidence, indent=2)
        elif self.instance and self.instance.pk:
            self.fields['evidence_json'].initial = '{}'
    
    def clean_evidence_json(self):
        """Clean dan parse evidence JSON dengan security checks"""
        evidence = self.cleaned_data.get('evidence_json', '')
        if not evidence or evidence.strip() == '':
            return {}
        
        # Limit JSON size to prevent DoS
        if len(evidence) > 10000:
            raise forms.ValidationError('Evidence JSON is too large. Maximum 10000 characters.')
        
        try:
            import json
            parsed = json.loads(evidence)
            
            # Ensure it's a dictionary
            if not isinstance(parsed, dict):
                raise forms.ValidationError('Evidence must be a JSON object (dictionary).')
            
            # Limit number of keys
            if len(parsed) > 50:
                raise forms.ValidationError('Evidence object cannot have more than 50 keys.')
            
            # Validate values are simple types (no nested objects/arrays)
            for key, value in parsed.items():
                if not isinstance(key, str):
                    raise forms.ValidationError('Evidence keys must be strings.')
                if not isinstance(value, (str, int, float, bool, type(None))):
                    raise forms.ValidationError('Evidence values must be simple types (string, number, boolean, null).')
            
            return parsed
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'Invalid JSON format: {str(e)}')
    
    def save(self, commit=True):
        punishment = super().save(commit=False)
        # Set evidence dari evidence_json (sudah di-parse di clean_evidence_json)
        evidence_data = self.cleaned_data.get('evidence_json', {})
        punishment.evidence = evidence_data if isinstance(evidence_data, dict) else {}
        if commit:
            punishment.save()
        return punishment

