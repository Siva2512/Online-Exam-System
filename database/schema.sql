-- ========================================================
-- ExamDesk / ExamHall Database Schema
-- Compatible with MySQL 8.x / Amazon RDS MySQL
-- ========================================================

CREATE DATABASE IF NOT EXISTS `examdesk` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `examdesk`;

-- Users table (students and administrators)
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(150) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `registration_number` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` VARCHAR(20) NOT NULL DEFAULT 'student',
    `department` VARCHAR(150) NOT NULL DEFAULT 'Computer Science',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_regno` (`registration_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Exams table
CREATE TABLE IF NOT EXISTS `exams` (
    `id` VARCHAR(50) PRIMARY KEY,
    `category` VARCHAR(100) NOT NULL,
    `code` VARCHAR(50) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT,
    `duration` INT NOT NULL DEFAULT 30, -- Duration in minutes
    `total_marks` INT NOT NULL DEFAULT 10,
    `pass_marks` INT NOT NULL DEFAULT 6,
    `status` VARCHAR(20) NOT NULL DEFAULT 'published',
    `show_answers` BOOLEAN NOT NULL DEFAULT TRUE,
    `opens_at` TIMESTAMP NULL DEFAULT NULL,
    `closes_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Multiple Choice Questions
CREATE TABLE IF NOT EXISTS `questions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `exam_id` VARCHAR(50) NOT NULL,
    `question_text` TEXT NOT NULL,
    `option_a` TEXT NOT NULL,
    `option_b` TEXT NOT NULL,
    `option_c` TEXT NOT NULL,
    `option_d` TEXT NOT NULL,
    `correct_option` INT NOT NULL, -- 0 for A, 1 for B, 2 for C, 3 for D
    `explanation` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`exam_id`) REFERENCES `exams`(`id`) ON DELETE CASCADE,
    INDEX `idx_questions_exam` (`exam_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Individual Exam Attempts and Results
CREATE TABLE IF NOT EXISTS `exam_attempts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `exam_id` VARCHAR(50) NOT NULL,
    `score` INT NOT NULL,
    `total_questions` INT NOT NULL,
    `percentage` DECIMAL(5,2) NOT NULL,
    `passed` BOOLEAN NOT NULL,
    `time_taken` INT NOT NULL, -- in minutes
    `answers_json` TEXT,
    `submitted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`exam_id`) REFERENCES `exams`(`id`) ON DELETE CASCADE,
    INDEX `idx_attempts_user` (`user_id`),
    INDEX `idx_attempts_exam` (`exam_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
