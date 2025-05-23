from flask import Blueprint, render_template, session, redirect, url_for
from mail_agent.models import User, Instruction
from mail_agent.forms import InstructionForm

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    user_info = None
    
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_info = {
                'name': user.name,
                'email': user.email,
                'created_at': user.created_at
            }
            
    return render_template('index.html', user_info=user_info)

@main_bp.route('/instructions')
def instructions():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_info = None
    instructions = []
    form = InstructionForm()
    has_system_instruction = False
    
    user = User.query.get(session['user_id'])
    if user:
        user_info = {
            'name': user.name,
            'email': user.email,
            'created_at': user.created_at,
            'processing_instructions': user.processing_instructions
        }
        # Get user's instructions, ordered with system first, then user instructions by creation date
        all_instructions = Instruction.query.filter_by(user_id=user.id).all()
        
        # Separate system and user instructions
        system_instructions = [i for i in all_instructions if i.instruction_type == 'system']
        user_instructions = [i for i in all_instructions if i.instruction_type == 'user']
        
        # Sort user instructions by creation date (newest first)
        user_instructions.sort(key=lambda x: x.created_at, reverse=True)
        
        # Combine with system first, then user instructions
        instructions = system_instructions + user_instructions
        has_system_instruction = len(system_instructions) > 0
        
    return render_template('instructions.html', 
                         user_info=user_info, 
                         instructions=instructions, 
                         form=form,
                         has_system_instruction=has_system_instruction)