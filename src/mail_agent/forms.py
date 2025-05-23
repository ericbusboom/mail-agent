from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class InstructionForm(FlaskForm):
    """Form for creating and editing instructions"""
    name = StringField('Instruction Name', validators=[Length(max=120)])
    content = TextAreaField('Instruction Content', validators=[DataRequired()])
    instruction_type = SelectField('Instruction Type', 
                                  choices=[('user', 'User'), ('system', 'System')],
                                  validators=[DataRequired()])
    submit = SubmitField('Save')
