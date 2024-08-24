from flask import Flask, render_template, request, redirect, url_for, flash,session
from forms import *
from models import *
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask import Flask, jsonify, request, url_for, redirect, flash
from flask_restful import Api, Resource, reqparse, abort
  
app = Flask(__name__)
app.static_folder = 'static'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///datab.sqlite3.db'
app.config['SECRET_KEY'] = '1234'

datab.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    flash('All fields are mandatory')
    form = Registration()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username taken. Please choose a different one')
            return render_template('register.html', form=form)
        if form.role.data == 'influencer':
            reach = form.reach.data
            if reach>=1000:
                niche = form.niche.data
            else:
                flash('Reach must be greater than or equal to 1000')
                return render_template('register.html', form=form)
        else:
            reach = None
            niche = None
        
        try:
            user = User(
                username=form.username.data,
                password=form.password.data,
                role=form.role.data,
                reach=reach,
                niche=niche,
                name=form.name.data
            )
            
            datab.session.add(user)
            datab.session.commit()
            flash('Registration successful.')
            return redirect(url_for('login'))
        except:
            datab.session.rollback()
            flash('Registration failed')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id
            if user.role == 'influencer' and user.flagged:
                flash('Your account is flagged. Contact Support')
                return redirect(url_for('login'))
            else:
                    return redirect(url_for(f'{user.role}_dashboard'))
        else:
            flash('Login unsuccessful. Please check Username and Password')
    return render_template('login.html', form=form)

@app.route('/')
def base():
    return render_template('base.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    active_users_count = User.query.count()
    public_campaigns_count = Campaign.query.filter_by(visibility='public').count()
    private_campaigns_count = Campaign.query.filter_by(visibility='private').count()
    ad_requests_count = AdRequest.query.count()
    flagged_users_count = User.query.filter_by(flagged=True).count()
    flagged_campaigns_count = Campaign.query.filter_by(flagged=True).count()

    histogram_data = [
        ('Active Users', active_users_count),
        ('Public Campaigns', public_campaigns_count),
        ('Private Campaigns', private_campaigns_count),
        ('Ad Requests', ad_requests_count),
        ('Flagged Users', flagged_users_count),
        ('Flagged Campaigns', flagged_campaigns_count)]

    maxi = max(active_users_count, public_campaigns_count, private_campaigns_count,
                ad_requests_count, flagged_users_count,flagged_campaigns_count)

    if request.method == 'POST':
        handle_flagging()

    campaigns = Campaign.query.all()
    ad_requests = AdRequest.query.all()

    return render_template('admin_dashboard.html', user=current_user,
                           active_users_count=active_users_count,
                           public_campaigns_count=public_campaigns_count,
                           private_campaigns_count=private_campaigns_count,
                           ad_requests_count=ad_requests_count,
                           flagged_users_count=flagged_users_count,
                           flagged_campaigns_count=flagged_campaigns_count,
                           histogram_data=histogram_data,
                           maxi=maxi,
                           campaigns=campaigns,
                           ad_requests=ad_requests)

def handle_flagging():
    username = request.form.get('username')
    name = request.form.get('name')

    if username:
        flag_user_by_username(username)
    elif name:
        flag_campaign(name)
    else:
        flash('No user or campaign selected for flagging')

def flag_user_by_username(username):
    if username == current_user.username:
        flash('Error: You cannot flag yourself.')
    else:
        user_to_flag = User.query.filter_by(username=username).first()
        if user_to_flag:
            user_to_flag.flagged = True
            datab.session.commit()
            flash(f'User {username} flagged successfully.')
        else:
            flash('Error: User not found.')

def flag_campaign(name):
    campaign_to_flag = Campaign.query.filter_by(name=name).first()
    if campaign_to_flag:
        campaign_to_flag.flagged = True
        datab.session.commit()
        flash(f'Campaign {campaign_to_flag.name} flagged successfully.')
    else:
        flash('Error: Campaign not found.')

@app.route('/sponsor_dashboard')
@login_required
def sponsor_dashboard():
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    if current_user.role != 'sponsor':
        flash('Sponsors can access this page')
        return redirect(url_for('base'))
    sponsor_campaigns = Campaign.query.filter_by(sponsor_id=current_user.id).all()
    return render_template('sponsor_dashboard.html', user=current_user, name=current_user.name,
                           campaigns=sponsor_campaigns)

@app.route('/influencer/dashboard')
@login_required
def influencer_dashboard():
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    influencer = User.query.filter_by(id=current_user.id).first()
    influencer_niche = influencer.niche
    influencer_reach = influencer.reach
    influencer_name = influencer.name
    active_campaigns = Campaign.query.filter_by(visibility='public',flagged=False).count()
    pending_requests = AdRequest.query.filter_by(status='pending', username=current_user.username).count()
    ongoing_negotiations = AdRequest.query.filter_by(status='Negotiated', username=current_user.username).count()
    ad_requests = AdRequest.query.filter_by(username=current_user.username).all()
    return render_template('influencer_dashboard.html',
                           niche=influencer_niche,
                           reach=influencer_reach,
                           name=influencer_name,
                           active_campaigns=active_campaigns,
                           pending_requests=pending_requests,
                           ongoing_negotiations=ongoing_negotiations,
                           ad_requests=ad_requests)


@app.route('/create_campaign', methods=['GET', 'POST'])
@login_required
def create_campaign():
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))

    form = CampaignForm()
    if form.validate_on_submit():
        existing_campaign = Campaign.query.filter_by(name=form.name.data).first()
        if existing_campaign:
            flash('Campaign name already taken. Please choose a different one.')
            return render_template('create_campaign.html', form=form)
        if form.end_date.data < form.start_date.data:
            flash('End date should be greater than start date.')
            return render_template('create_campaign.html', form=form)
        if form.budget.data < 0:
            flash('Budget must be greater than 0.')
            return render_template('create_campaign.html', form=form)
        campaign = Campaign(
            name=form.name.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            budget=form.budget.data,
            visibility=form.visibility.data,
            sponsor_id=current_user.id
        )
        datab.session.add(campaign)
        datab.session.commit()
        flash("Campaign created successfully.")
        return redirect(url_for('sponsor_dashboard'))

    return render_template('create_campaign.html', form=form)
@app.route('/update_campaign/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
def update_campaign(campaign_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.sponsor_id != current_user.id:
        flash('You are not authorized to update this campaign.')
        return redirect(url_for('sponsor_dashboard'))
    form = CampaignForm()
    if form.validate_on_submit():
        if form.end_date.data <= form.start_date.data:
            flash('End date must be greater than start date.')
            return render_template('update_campaign.html', form=form, campaign=campaign)
        if form.budget.data < 0:
            flash('Budget must be greater than 0')
            return render_template('update_campaign.html', form=form, campaign=campaign)
        campaign.name = form.name.data
        campaign.description = form.description.data
        campaign.start_date = form.start_date.data
        campaign.end_date = form.end_date.data
        campaign.budget = form.budget.data
        campaign.visibility = form.visibility.data
        datab.session.commit()
        flash('Campaign updated successfully.')
        return redirect(url_for('sponsor_dashboard'))
    elif request.method == 'GET':
        form.name.data = campaign.name
        form.description.data = campaign.description
        form.start_date.data = campaign.start_date
        form.end_date.data = campaign.end_date
        form.budget.data = campaign.budget
        form.visibility.data = campaign.visibility
    return render_template('update_campaign.html', form=form, campaign=campaign)

@app.route('/delete_campaign/<int:campaign_id>', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    campaign = Campaign.query.get_or_404(campaign_id)
    datab.session.delete(campaign)
    datab.session.commit()
    return redirect(url_for('sponsor_dashboard'))

@app.route('/create_ad_request/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
def create_ad_request(campaign_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    form = Ad_RequestForm()
    campaign = Campaign.query.get_or_404(campaign_id)
    if form.validate_on_submit():
        ad_request_amount = float(form.payment_amount.data)
        if ad_request_amount < 0:
            flash('Ad request amount must be greater than equal to zero.')
        elif ad_request_amount > campaign.budget:
            flash('Ad request amount should not exceed the campaign budget')
        else:
            username = form.username.data
            ad_request = AdRequest(
                campaign_id=campaign_id,
                username=username,
                messages=form.messages.data,
                payment_details= form.payment_details.data,
                requirements=form.requirements.data,
                payment_amount=ad_request_amount,
                status=form.status.data
            )
            datab.session.add(ad_request)
            datab.session.commit()
            flash('Ad request created successfully')
            return redirect(url_for('sponsor_dashboard'))
    return render_template('create_ad_request.html', form=form, campaign=campaign)

@app.route('/update_ad_request/<int:ad_request_id>', methods=['GET', 'POST'])
@login_required
def update_ad_request(ad_request_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    form = Ad_RequestForm(obj=ad_request)
    if form.validate_on_submit():
        ad_request_amount = float(form.payment_amount.data)
        campaign = Campaign.query.get(ad_request.campaign_id)
        if ad_request_amount < 0:
            flash('Ad request amount must be greater than equal to zero.')
        elif ad_request_amount > campaign.budget:
            flash('Ad request amount should not exceed the campaign budget')
        else:
            ad_request.username = form.username.data
            ad_request.messages = form.messages.data
            ad_request.payment_details= form.payment_details.data
            ad_request.requirements = form.requirements.data
            ad_request.payment_amount = ad_request_amount
            ad_request.status = form.status.data
            datab.session.commit()
            flash('Ad request updated successfully')
            return redirect(url_for('sponsor_dashboard'))
    return render_template('update_ad_request.html', form=form, ad_request=ad_request)

@app.route('/delete_ad_request/<int:ad_request_id>', methods=['POST'])
@login_required
def delete_ad_request(ad_request_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    datab.session.delete(ad_request)
    datab.session.commit()
    flash('Ad request deleted successfully')
    return redirect(url_for('sponsor_dashboard'))

@app.route('/search_influencers', methods=['GET', 'POST'])
def search_influencers():
    form = SearchInfluencer()
    if current_user.role == 'influencer':
        query = User.query.filter_by(role='influencer')
    else:
        query = User.query.filter_by(role='influencer')
    if form.validate_on_submit():
        name_keyword = form.name.data.lower()
        reach_keyword = form.reach.data
        if name_keyword:
            query = query.filter(User.name.ilike(f'%{name_keyword}%'))
        if reach_keyword:
            query = query.filter(User.reach >= reach_keyword)
        influencers = query.all()
        return render_template('search_influencers.html', form=form, influencers=influencers)
    influencers = query.all()
    return render_template('search_influencers.html', form=form, influencers=influencers)

@app.route('/view_campaigns', methods=['GET', 'POST'])
def view_campaigns():
    form = SearchCampaign()
    if form.validate_on_submit():
        name_keyword = form.name.data.lower()
        campaign = Campaign.query.filter(Campaign.name.ilike(f'%{name_keyword}%'), 
                                         Campaign.visibility == 'public',Campaign.flagged == False).first()
        return render_template('view_campaigns.html', form=form, campaigns=[campaign] if campaign else [])
    campaigns = Campaign.query.filter_by(visibility='public',flagged = False).all()
    return render_template('view_campaigns.html', form=form, campaigns=campaigns)


# @app.route('/edit_profile', methods=['GET', 'POST'])
# @login_required
# def edit_profile():
#     flash('Deletion is one time permanent and irreversible')
#     user_id = session.get('user_id')
#     if user_id != current_user.id:
#         flash('Please log in again.')
#         return redirect(url_for('logout'))
    
#     influencer = User.query.get(current_user.id)
    
#     if request.args.get('delete'):
#         datab.session.delete(influencer)
#         datab.session.commit()
#         flash('Your profile has been deleted.')
#         logout_user()
#         return redirect(url_for('base'))
    
#     form = EditProfileInfluencer(obj=influencer)
#     if form.validate_on_submit():
#         form.populate_obj(influencer)
#         datab.session.commit()
#         flash('Profile updated successfully')
#         return redirect(url_for('influencer_dashboard'))
#     return render_template('edit_profile.html', form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    flash('Deletion is one time permanent and irreversible')
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    
    influencer = User.query.get(current_user.id)
    
    if request.method == 'POST' and request.form.get('delete_confirm'):
        datab.session.delete(influencer)
        datab.session.commit()
        logout_user()
        return redirect(url_for('base'))
    
    form = EditProfileInfluencer(obj=influencer)
    if form.validate_on_submit():
        try:
            form.populate_obj(influencer)
            datab.session.commit()
            flash('Profile updated successfully')
            return redirect(url_for('influencer_dashboard'))
        except:
            datab.session.rollback()
            flash('Updation failed,username taken')
    return render_template('edit_profile.html', form=form)
    

@app.route('/sponsor_edit_profile', methods=['GET', 'POST'])
@login_required
def sponsor_edit_profile():
    flash('Deletion is one time permanent and irreversible, Delete Campaign and Ad Request First')
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))

    sponsor = User.query.get(current_user.id)
    
    if request.method == 'POST' and request.form.get('delete_confirm'):
        datab.session.delete(sponsor)
        datab.session.commit()
        logout_user()
        return redirect(url_for('base'))
    
    form = SponsorEditProfile(obj=sponsor)
    if form.validate_on_submit():
        try:
            form.populate_obj(sponsor)
            datab.session.commit()
            flash('Profile updated successfully')
            return redirect(url_for('sponsor_dashboard'))
        except:
            datab.session.rollback()
            flash('Updation failed,username taken')
    return render_template('sponsor_edit_profile.html', form=form)

@app.route('/view_ad_requests/<username>', methods=['GET'])
@login_required
def view_ad_requests(username):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    influencer = User.query.filter_by(username=username).first()
    if not influencer:
        flash('Influencer not found')
        return redirect(url_for('influencer_dashboard'))
    ad_requests = AdRequest.query.filter_by(username=username).all()
    return render_template('view_ad_requests.html', influencer=influencer, ad_requests=ad_requests)

@app.route('/accept_ad_request/<int:ad_request_id>', methods=['GET','POST'])
@login_required
def accept_ad_request(ad_request_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    if ad_request.status != 'Accepted':
        form = Ad_RequestForm(obj=ad_request)  # Pre-populating form with the existing data
        if form.validate_on_submit():
            ad_request.payment_details = form.payment_details.data
            ad_request.status = 'Accepted'
            datab.session.commit()
            flash('Ad request accepted successfully')
            return redirect(url_for('view_ad_requests', username=ad_request.username))
    else:
        flash('Ad request has already been accepted')
        return redirect(url_for('view_ad_requests', username=ad_request.username))
    return render_template('accept_ad_request.html', form=form, ad_request=ad_request)

@app.route('/reject_ad_request/<int:ad_request_id>', methods=['POST'])
@login_required
def reject_ad_request(ad_request_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))
    ad_request = AdRequest.query.get_or_404(ad_request_id)
    if ad_request.status != 'Rejected':
        ad_request.status = 'Rejected'
        datab.session.commit()
        flash('Ad request rejected successfully')
    else:
        flash('Ad request has already been rejected')
    return redirect(url_for('view_ad_requests',username=ad_request.username))

@app.route('/negotiate_ad_request/<int:ad_request_id>', methods=['GET', 'POST'])
@login_required
def negotiate_ad_request(ad_request_id):
    user_id = session.get('user_id')
    if user_id != current_user.id:
        flash('Please log in again.')
        return redirect(url_for('logout'))

    ad_request = AdRequest.query.get_or_404(ad_request_id)
    if ad_request.status != 'Negotiated':
        form = Ad_RequestForm(obj=ad_request)  # Pre-populating form with the existing data
        if form.validate_on_submit():
            ad_request.messages = form.messages.data
            ad_request.status = 'Negotiated'
            datab.session.commit()
            flash('Ad request negotiated successfully')
            return redirect(url_for('view_ad_requests', username=ad_request.username))
    else:
        flash('Ad request has already been negotiated')
        return redirect(url_for('view_ad_requests', username=ad_request.username))
    return render_template('negotiate_ad_request.html', form=form, ad_request=ad_request)


@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.clear() 
    logout_user()
    return redirect(url_for('base'))


@app.route('/contact')
def contact():
    contact_info = "Contact page is yet to develop, please call 9804183208 for further assistance"
    return render_template('contact.html', contact_info=contact_info)

@app.route('/support')
def support():
    return render_template('support.html')


if __name__ == '__main__':
    app.run(debug=True)

