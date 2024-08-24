from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FloatField, DateField,IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, Optional,NumberRange,ValidationError,input_required
from models import User

class Login(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

def validinfluencer(form, field):
    if form.role.data == 'influencer' and not field.data:
        raise ValidationError('Mandatory field for influencers.')

class Registration(FlaskForm):
    username = StringField('Username', validators=[DataRequired(),Length(min=4, max=12, message="minimum 4 bytes")])
    password = PasswordField('Password', validators=[DataRequired(),Length(min=4, max=8, message="minimum 4 bytes")])
    role = SelectField('Role', choices=[('influencer', 'Influencer'), ('sponsor', 'Sponsor')], validators=[DataRequired()])
    reach = IntegerField('Reach', validators=[validinfluencer])
    niche = StringField('Niche', validators=[validinfluencer])
    name = StringField('Name', validators=[DataRequired()])

class CampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired(), Length(min=2, max=150)])
    description = TextAreaField('Description', validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    budget = FloatField('Budget', validators=[DataRequired()])
    visibility = SelectField('Visibility', choices=[('public', 'Public'), ('private', 'Private')], validators=[DataRequired()])
    submit = SubmitField('Create Campaign')

class Ad_RequestForm(FlaskForm):
    username = SelectField('Influencer Username', validators=[DataRequired()])
    requirements = StringField('Requirements', validators=[Optional()])
    payment_amount = FloatField('Payment Amount', validators=[DataRequired()])
    messages= StringField('Messages', validators=[Optional()])
    payment_details= StringField('Payment Details', validators=[Optional()])
    status = SelectField('Status', choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], validators=[DataRequired()])
    #status = SelectField('Status', choices=[('pending', 'Pending')], validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username.choices = [(user.username, user.username) for user in User.query.filter_by(role='influencer').all()]

class SearchCampaign(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired(), Length(min=2, max=150)])
    submit = SubmitField('Search')
    back= SubmitField('Back')

class SearchInfluencer(FlaskForm):
    name = StringField('Influencer Name', validators=[Optional(), Length(min=2, max=150)])
    reach = IntegerField('Minimum Reach', validators=[Optional(), NumberRange(min=1000, message='Reach must be >=1000')])
    submit = SubmitField('Search')

class EditProfileInfluencer(FlaskForm):
    niche = StringField('Niche', validators=[Optional()])
    reach = IntegerField('Reach', validators=[Optional(), NumberRange(min=1000, message='Reach must be greater than 999')])
    username = StringField('New Username', validators=[Optional()])
    password = PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField('Save Changes')

class SponsorEditProfile(FlaskForm):
    username = StringField('New Username', validators=[Optional()])
    password = PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField('Save Changes')
