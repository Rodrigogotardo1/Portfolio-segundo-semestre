import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zerodengue_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zerodengue.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos
class Cadastro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    nascimento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(9), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    usuario = db.relationship('Usuario', backref='cadastro', uselist=False)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    senha = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(50), nullable=False, unique=True)
    contato = db.Column(db.String(11))
    estado = db.Column(db.String(2), nullable=False)
    cidade = db.Column(db.String(25), nullable=False)
    bairro = db.Column(db.String(50), nullable=False)
    rua = db.Column(db.String(50), nullable=False)
    fk_cadastro_id = db.Column(db.Integer, db.ForeignKey('cadastro.id'), nullable=False)
    denuncias = db.relationship('Denuncia', backref='usuario', lazy=True)
    funcionario = db.relationship('Funcionario', backref='usuario', uselist=False)

class Denuncia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endereco = db.Column(db.String(50), nullable=False)
    bairro = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text)
    latitude = db.Column(db.Float)  # Novo campo
    longitude = db.Column(db.Float) # Novo campo
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow) # Novo campo para ordenar
    status = db.Column(db.String(20), default='Em Análise') # Novo campo de status
    fk_usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    imagens = db.relationship('Imagem', backref='denuncia', lazy=True)
    relatorios = db.relationship('Relatorio', backref='denuncia', lazy=True)

class Imagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagem = db.Column(db.LargeBinary, nullable=False)
    fk_denuncia_id = db.Column(db.Integer, db.ForeignKey('denuncia.id'), nullable=False)

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cargo = db.Column(db.String(50), default='Administrador')
    fk_usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    relatorios = db.relationship('Relatorio', backref='funcionario', lazy=True)

class Relatorio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    relatorio = db.Column(db.Text, nullable=False)
    conclusao = db.Column(db.String(255), nullable=False)
    data_relatorio = db.Column(db.DateTime, default=datetime.utcnow)
    fk_denuncia_id = db.Column(db.Integer, db.ForeignKey('denuncia.id'), nullable=False)
    fk_funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)

# Criar banco de dados se não existir
with app.app_context():
    db.create_all()

# Helper para checar se é admin
def is_admin(user_id):
    user = Usuario.query.get(user_id)
    return user and user.funcionario is not None

@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    admin = False
    if user_id:
        admin = is_admin(user_id)
    return dict(is_admin_global=admin)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        user = Usuario.query.filter_by(email=email).first()
        if user and check_password_hash(user.senha, senha):
            session['user_id'] = user.id
            flash('Login realizado com sucesso!', 'success')
            
            if is_admin(user.id):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos.', 'danger')
            
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # Cadastro
        nome = request.form.get('nome')
        nascimento_str = request.form.get('nascimento')
        sexo = request.form.get('sexo')
        cpf = request.form.get('cpf')
        
        # Usuario
        email = request.form.get('email')
        senha = request.form.get('senha')
        contato = request.form.get('contato')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')
        bairro = request.form.get('bairro')
        rua = request.form.get('rua')
        
        if Usuario.query.filter_by(email=email).first():
            flash('Este email já está cadastrado.', 'danger')
            return redirect(url_for('cadastro'))
            
        try:
            nascimento = datetime.strptime(nascimento_str, '%Y-%m-%d').date()
            novo_cadastro = Cadastro(nome=nome, nascimento=nascimento, sexo=sexo, cpf=cpf)
            db.session.add(novo_cadastro)
            db.session.flush() 
            
            senha_hash = generate_password_hash(senha)
            novo_usuario = Usuario(
                senha=senha_hash, email=email, contato=contato,
                estado=estado, cidade=cidade, bairro=bairro, rua=rua,
                fk_cadastro_id=novo_cadastro.id
            )
            db.session.add(novo_usuario)
            db.session.commit()
            
            flash('Cadastro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')

    return render_template('cadastro.html', is_admin_registration=False)

@app.route('/cadastro-admin', methods=['GET', 'POST'])
def cadastro_admin():
    if request.method == 'POST':
        # O mesmo fluxo do cadastro, mas no final adiciona como Funcionario
        nome = request.form.get('nome')
        nascimento_str = request.form.get('nascimento')
        sexo = request.form.get('sexo')
        cpf = request.form.get('cpf')
        
        email = request.form.get('email')
        senha = request.form.get('senha')
        contato = request.form.get('contato')
        estado = request.form.get('estado')
        cidade = request.form.get('cidade')
        bairro = request.form.get('bairro')
        rua = request.form.get('rua')
        
        if Usuario.query.filter_by(email=email).first():
            flash('Este email já está cadastrado.', 'danger')
            return redirect(url_for('cadastro_admin'))
            
        try:
            nascimento = datetime.strptime(nascimento_str, '%Y-%m-%d').date()
            novo_cadastro = Cadastro(nome=nome, nascimento=nascimento, sexo=sexo, cpf=cpf)
            db.session.add(novo_cadastro)
            db.session.flush() 
            
            senha_hash = generate_password_hash(senha)
            novo_usuario = Usuario(
                senha=senha_hash, email=email, contato=contato,
                estado=estado, cidade=cidade, bairro=bairro, rua=rua,
                fk_cadastro_id=novo_cadastro.id
            )
            db.session.add(novo_usuario)
            db.session.flush()
            
            # Adiciona funcionario
            novo_funcionario = Funcionario(cargo='Agente de Saúde', fk_usuario_id=novo_usuario.id)
            db.session.add(novo_funcionario)
            
            db.session.commit()
            
            flash('Conta de Administrador criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')

    return render_template('cadastro_admin.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = Usuario.query.get(session['user_id'])
    denuncias = Denuncia.query.filter_by(fk_usuario_id=user.id).order_by(Denuncia.data_criacao.desc()).all()
    
    return render_template('dashboard.html', user=user, denuncias=denuncias, is_admin=is_admin(user.id))

@app.route('/nova-denuncia', methods=['GET', 'POST'])
def nova_denuncia():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        endereco = request.form.get('endereco')
        bairro = request.form.get('bairro')
        descricao = request.form.get('descricao')
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')
        user_id = session['user_id']
        
        latitude = float(lat) if lat else None
        longitude = float(lng) if lng else None
        
        nova_denuncia = Denuncia(endereco=endereco, bairro=bairro, descricao=descricao, 
                               latitude=latitude, longitude=longitude, fk_usuario_id=user_id)
        db.session.add(nova_denuncia)
        db.session.commit()
        
        flash('Denúncia registrada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('nova_denuncia.html', user_id=session.get('user_id'), is_admin=is_admin(session.get('user_id')))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not is_admin(session['user_id']):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))
        
    user = Usuario.query.get(session['user_id'])
    todas_denuncias = Denuncia.query.order_by(Denuncia.data_criacao.desc()).all()
    
    return render_template('admin_dashboard.html', user=user, denuncias=todas_denuncias, is_admin=True)

@app.route('/admin/relatorio/<int:id>', methods=['POST'])
def criar_relatorio(id):
    if 'user_id' not in session or not is_admin(session['user_id']):
        return redirect(url_for('index'))
        
    user = Usuario.query.get(session['user_id'])
    denuncia = Denuncia.query.get_or_404(id)
    
    relatorio_texto = request.form.get('relatorio')
    conclusao = request.form.get('conclusao')
    
    novo_relatorio = Relatorio(
        relatorio=relatorio_texto,
        conclusao=conclusao,
        fk_denuncia_id=denuncia.id,
        fk_funcionario_id=user.funcionario.id
    )
    
    denuncia.status = 'Concluído'
    db.session.add(novo_relatorio)
    db.session.commit()
    
    flash('Relatório salvo e denúncia concluída!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
