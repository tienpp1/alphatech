from django import forms
from apps.notifications.models import InternalBulletin


class BulletinEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["style"] = "width:100%;max-width:100%;box-sizing:border-box;"

    class Meta:
        model = InternalBulletin
        fields = ("title", "content", "priority")
        labels = {"title": "Tiêu đề", "content": "Nội dung", "priority": "Mức độ ưu tiên"}
        widgets = {"content": forms.Textarea(attrs={"rows": 8})}

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("Vui lòng nhập nội dung bản tin.")
        return content
