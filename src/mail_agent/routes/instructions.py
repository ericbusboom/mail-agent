from flask import Blueprint, request, redirect, url_for, flash, session, render_template, jsonify
from mail_agent.models import db, Instruction, User
from mail_agent.forms import InstructionForm
from datetime import datetime, timezone

instructions_bp = Blueprint('instructions', __name__)

@instructions_bp.route('/instructions/create', methods=['POST'])
def create_instruction():
    if 'user_id' not in session:
        return redirect('/login')
    
    form = InstructionForm()
    
    if form.validate_on_submit():
        # If it's a system instruction, use a default name if not provided
        name = form.name.data.strip() if form.name.data else None
        if form.instruction_type.data == 'system' and not name:
            name = f"System Instruction {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        elif form.instruction_type.data == 'user' and not name:
            flash('Name is required for user instructions')
            return redirect(url_for('main.instructions'))
            
        # Create new instruction
        instruction = Instruction( 
            name=name,# type: ignore
            content=form.content.data, # type: ignore
            instruction_type=form.instruction_type.data,# type: ignore
            user_id=session['user_id']# type: ignore
        )
        
        db.session.add(instruction)
        db.session.commit()
        flash('Instruction created successfully')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}")
    
    return redirect(url_for('main.instructions'))

@instructions_bp.route('/instructions/update/<int:id>', methods=['POST'])
def update_instruction(id):
    if 'user_id' not in session:
        return redirect('/login')
    
    # Get instruction
    instruction = Instruction.query.get_or_404(id)
    
    # Check if the instruction belongs to the user
    if instruction.user_id != session['user_id']:
        flash('You do not have permission to edit this instruction')
        return redirect(url_for('main.instructions'))
    
    # Create form and validate
    form = InstructionForm()
    if form.validate_on_submit():

        # Update instruction name
        if form.instruction_type.data == 'system' :
            # Generate a default name for system instructions
            instruction.name = f"System Instruction {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        else:

            if not form.name.data or not form.name.data.strip():
                flash('Name is required for user instructions')
                return redirect(url_for('main.instructions'))    

            instruction.name = form.name.data.strip()
            
        # Update content and type
        instruction.content = form.content.data
        instruction.instruction_type = form.instruction_type.data
        instruction.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash('Instruction updated successfully')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}")
    
    return redirect(url_for('main.instructions'))

@instructions_bp.route('/instructions/delete/<int:id>')
def delete_instruction(id):
    if 'user_id' not in session:
        return redirect('/login')
    
    # Get instruction
    instruction = Instruction.query.get_or_404(id)
    
    # Check if the instruction belongs to the user
    if instruction.user_id != session['user_id']:
        flash('You do not have permission to delete this instruction')
        return redirect(url_for('main.instructions'))
    
    # Delete instruction
    db.session.delete(instruction)
    db.session.commit()
    
    return redirect(url_for('main.instructions'))

@instructions_bp.route('/instructions/get/<int:id>')
def get_instruction(id):
    """Get instruction data for modal editing"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    instruction = Instruction.query.get_or_404(id)
    
    # Check if the instruction belongs to the user
    if instruction.user_id != session['user_id']:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'id': instruction.id,
        'name': instruction.name,
        'content': instruction.content,
        'instruction_type': instruction.instruction_type
    })
